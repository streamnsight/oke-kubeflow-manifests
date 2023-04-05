import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
from time import sleep
from subprocess import Popen, PIPE


# default input files
ENV_FILE='kubeflow.env'
ENV_TEMPLATE_FILE='kubeflow.tmpl.env'
KUBEFLOW_VERSION_FILE='kubeflow_version.env'


# variable example and pattern for validation
variable_specs = {
    'OCI_KUBEFLOW_DOMAIN_NAME': {
        'example': 'mydomain.com',
        'pattern': r'[a-z0-9.]+',
    },
    'OCI_KUBEFLOW_DOMAIN_ADMIN_EMAIL': {
        'example': 'admin@mydomain.com',
        'pattern': None
    },
    'OCI_KUBEFLOW_DNS_ZONE_COMPARTMENT_OCID': {
        'example': 'ocid1.compartment.oc1...',
        'pattern': r'ocid1\.compartment\.oc.*'
    },
    'OCI_KUBEFLOW_IDCS_URL': {
        'example': 'https://idcs-xxxxxx.identity.oraclecloud.com',
        'pattern': r'https://idcs-.*\.identity.oraclecloud.com$',
        'help': 'refer to docs/idcs.md to setup an IDCS Application for KubeFlow'
    },
    'OCI_KUBEFLOW_IDCS_CLIENT_ID': {
        'example': 'e140ade85eec47748df546d3ba6aeca8',
        'pattern': r'[a-f0-9]{32}',
        'help': 'refer to docs/idcs.md to setup an IDCS Application for KubeFlow'

    },
    'OCI_KUBEFLOW_IDCS_CLIENT_SECRET': {
        'example': '0943f5de-eae2-4a68-c9db-d5380fe933b4',
        'pattern': r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}',
        'help': 'refer to docs/idcs.md to setup an IDCS Application for KubeFlow'
    },
    'OCI_KUBEFLOW_MYSQL_USER': {
        'example': 'kubeflow',
        'pattern': r'[a-zA-Z0-9_]+',
        'help': 'refer to docs/mysql.md to deploy a MySQL DB for KubeFlow. Important: a DNS hostname must be provided.'
    },
    'OCI_KUBEFLOW_MYSQL_PASSWORD': {
        'example': 'wIw_MqkrPrT9LuZcIhot[]1EPd7w7ll',
        'pattern': r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!#$%&'()*+/:;<=>?@_`{|}~,[\]\-\.])[A-Za-z\d!#$%&'()*+/:;<=>?@_`{|}~,[\]\-\.]{8,32}$",
        'help': 'refer to docs/mysql.md to deploy a MySQL DB for KubeFlow. Important: a DNS hostname must be provided.'
    },
    'OCI_KUBEFLOW_MYSQL_HOST': {
        'example': '',
        'pattern': r'.*\.oraclevcn.com',
        'help': 'refer to docs/mysql.md to deploy a MySQL DB for KubeFlow. Important: a DNS hostname must be provided.'        
    },
    'OCI_KUBEFLOW_MYSQL_PORT': {
        'example': '3306',
        'pattern': r'3306',
        'help': 'refer to docs/mysql.md to deploy a MySQL DB for KubeFlow. '
    },
    'OCI_KUBEFLOW_OBJECT_STORAGE_REGION': {
        'example': 'us-ashburn-1',
        'pattern': r'[a-z]{2}-[a-z]+-[0-9]+'
    },
    'OCI_KUBEFLOW_OBJECT_STORAGE_BUCKET': {
        'example': 'name-kubeflow-metadata',
        'pattern': r'[a-zA-Z0-9_-]+'
    },
    'OCI_KUBEFLOW_OBJECT_STORAGE_NAMESPACE': {
        'example': 'mynamespace',
        'pattern': r'[a-zA-Z0-9_-]+'
    },
    'OCI_KUBEFLOW_OBJECT_STORAGE_ACCESS_KEY': {
        'example': '5cc417c90231c7dc02a9cd90e6f6ac301e46c282',
        'pattern': r'[a-f0-9]{40}'
    },
    'OCI_KUBEFLOW_OBJECT_STORAGE_SECRET_KEY': {
        'example': 'sdwAAerQWE123fre3245SDFEw334=',
        'pattern': r'[a-zA-Z0-9+=]+'
    }
}
# variables required by each add-on
add_on_variables = {
    'letsencrypt-http01': [
        'OCI_KUBEFLOW_DOMAIN_NAME',
        'OCI_KUBEFLOW_DOMAIN_ADMIN_EMAIL'
    ],
    'letsencrypt-dns01': [
        'OCI_KUBEFLOW_DOMAIN_NAME',
        'OCI_KUBEFLOW_DOMAIN_ADMIN_EMAIL',
        'OCI_KUBEFLOW_DNS_ZONE_COMPARTMENT_OCID'
    ],
    'idcs': [
        'OCI_KUBEFLOW_IDCS_URL',
        'OCI_KUBEFLOW_IDCS_CLIENT_ID',
        'OCI_KUBEFLOW_IDCS_CLIENT_SECRET'
    ],
    'external-mysql': [
        'OCI_KUBEFLOW_MYSQL_USER',
        'OCI_KUBEFLOW_MYSQL_PASSWORD',
        'OCI_KUBEFLOW_MYSQL_HOST',
        'OCI_KUBEFLOW_MYSQL_PORT'
    ],
    'oci-object-storage': [
        'OCI_KUBEFLOW_OBJECT_STORAGE_REGION',
        'OCI_KUBEFLOW_OBJECT_STORAGE_BUCKET',
        'OCI_KUBEFLOW_OBJECT_STORAGE_NAMESPACE',
        'OCI_KUBEFLOW_OBJECT_STORAGE_ACCESS_KEY',
        'OCI_KUBEFLOW_OBJECT_STORAGE_SECRET_KEY'
    ]
}


log = logging.getLogger(__file__)
formatter = logging.Formatter('[%(asctime)s][%(levelname)-7s] %(message)s', "%y-%m-%d %H:%M:%S")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
log.addHandler(handler)
if os.environ.get('DEBUG', False):
    log.setLevel(logging.DEBUG)

no_prompts = False
env = None


def run_shell_cmd(cmd, shell=False, verbose=True):
    if verbose:
        log.info(cmd)
    if shell is False:
        cmd = cmd.split()
    p = Popen(cmd, shell=shell, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    while p.poll() is None:
        line = p.stdout.readline()
        log.info(line.decode('utf-8').rstrip())
    log.debug(f'return code: {p.returncode}')
    return p.returncode


class DependenciesValidator():
    versions = None

    def __init__(self):
        self.parse_versions_file()

    def validate_dependencies(self):
        log.info('Validating required dependencies.')
        valid = True
        valid = valid & self.validate_kubectl()
        valid = valid & self.validate_kustomize()
        valid = valid & self.validate_oci_cli()
        valid = valid & self.validate_k8s_version()
        if valid:
            log.info('Dependency validation passed.')
        else:
            log.error('Dependency validation failed.')
            exit(1)

    def parse_versions_file(self):
        if self.versions is None:
            self.versions = {}
            with open(KUBEFLOW_VERSION_FILE, 'r') as f:
                kf_version_file_content = f.readlines()
                for line in kf_version_file_content:
                    if line[0] != '#':
                        k, v = line.strip().split('=', 1)
                        self.versions[k] = v.replace('"','')
        if self.versions.get('KUBEFLOW_RELEASE_VERSION') is None:
            log.error('KUBEFLOW_RELEASE_VERSION version not found in "kubeflow_version.env" file.')
            exit(1)
        return self.versions

    def validate_kubectl(self):
        try:
            subprocess.check_output('command -v kubectl &>/dev/null', shell=True)
            log.info('kubectl found.')
            return True
        except subprocess.CalledProcessError as e:
            log.error('error looking for kubectl')
            return False

    def validate_kustomize(self):
        major_min = self.versions.get('KUSTOMIZE_MIN_VERSION_MAJOR')
        minor_min = self.versions.get('KUSTOMIZE_MIN_VERSION_MINOR')
        try:
            output = subprocess.check_output('kustomize version --short', shell=True)
            match = re.search(r'(\d+\.\d+\.\d+)', output.decode('utf-8'))
            if match:
                version = match.group(0)
                major, minor, _ = version.split('.')
                if not (int(major) >= int(major_min) and int(minor) >= int(minor_min)):
                    log.error(f'kustomize v{version} is too old. Setup requires v{major_min}.{minor_min}+')
                    return False
                else:
                    log.info(f'kustomize v{version} found.')
                    return True
        except subprocess.CalledProcessError as e:
            log.error('kustomize not found')
            return False

    def validate_oci_cli(self):
        try:
            subprocess.check_output('command -v oci &>/dev/null', shell=True)
            log.info('oci cli found.')
            return True
        except subprocess.CalledProcessError as e:
            log.error('error looking for the oci cli')
            return False

    def validate_k8s_version(self):
        kf_version = self.versions.get('KUBEFLOW_RELEASE_VERSION')
        major_min = self.versions.get('KUBEFLOW_MIN_K8S_VERSION_MAJOR')
        major_max = self.versions.get('KUBEFLOW_MAX_K8S_VERSION_MAJOR')
        minor_min = self.versions.get('KUBEFLOW_MIN_K8S_VERSION_MINOR')
        minor_max = self.versions.get('KUBEFLOW_MAX_K8S_VERSION_MINOR')
        log.info(f'Validating Kubernetes server version for KubeFlow')
        log.info(f'KubeFlow {kf_version} requires Kubernetes server v{major_min}.{minor_min} to v{major_max}.{minor_max}')
        cmd = 'kubectl version --short'
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        while p.poll() is None:
            line = p.stdout.readline()
            line = line.decode('utf-8').rstrip()
            log.info(line)
            if 'Server' in line:
                match = re.search(r'\d+\.\d+\.\d+', line)
                log.debug(match[0])
                if match is not None:
                    major, minor, _ = match[0].split('.')
                    if (major_min <= major <= major_max) and (minor_min <= minor <= minor_max):
                        log.info('Kubernetes server version validated.')
                        return True
                    else:
                        log.error('Kubernetes server version does not match requirements.')
                        return False
        log.error('Enable to lookup Kubernetes server version. Check that kubectl is configured to connect to an existing cluster.')
        return False


class EnvironmentManager():
    env = None
    no_prompts = False

    def __init__(self, env_file=ENV_FILE, no_prompts=False):
        self.env_file = env_file
        self.no_prompts = no_prompts
        self.parse_kubeflow_env()

    def parse_kubeflow_env(self):
        cwd = os.getcwd()
        env_file_path = os.path.join(cwd, self.env_file)
        if self.env is None:
            # if env file does not exist, try to create it from template
            if not os.path.exists(env_file_path):
                log.error(f'Environment file "{self.env_file}" not found. Creating new one from template.')
                env_tmpl_file_path = os.path.join(cwd, ENV_TEMPLATE_FILE)
                if not os.path.exists(env_tmpl_file_path):
                    log.error(f'Environment file template "{ENV_TEMPLATE_FILE}" not found. Creating empty file.')
                    open(env_file_path, 'a').close()
                else:
                    shutil.copy(env_tmpl_file_path, env_file_path)
            self.env = {}
            with open(env_file_path, 'r') as f:
                config = f.readlines()
                for line in config:
                    line=line.strip()
                    if len(line) > 0 and line[0] != '#':
                        log.debug(line)
                        k, v = line.strip().split('=', 1)
                        self.env[k] = v.replace('"', '')
        return self.env

    def validate_pattern(self, variable, value, error=True):
        example = variable_specs[variable]['example']
        pattern = variable_specs[variable]['pattern']
        if pattern is not None:
            log.debug(re.match(pattern, value))
            if re.match(pattern, value) is None:
                if error:
                    log.error(f'{value} does not match the required pattern "{pattern}", for example: {example}')
                return False
        return True

    def validate_env_variable(self, variable, save=True):
        if variable not in variable_specs.keys():
            raise ValueError(f'{variable} is not a recognized variable.')
        val = self.env.get(variable)
        val_orig = val
        while val is None or val == '':
            if self.no_prompts:
                raise ValueError(f'{variable} is not defined. Edit the env file or run the "okf config" command to configure missing variables.')
            val = input(f'{variable} is not defined. Please enter a value: \n> ')
            val = val.strip()
            if not self.validate_pattern(variable, val):
                val = ''
        if val != val_orig and save is True:
            self.save_variable(variable, val)

    def save_variable(self, variable, val):
        log.debug(f'Saving: {variable}')
        self.env[variable] = val
        cwd = os.getcwd()
        content = None
        with open(os.path.join(cwd, self.env_file), 'r') as f:
            content = f.readlines()
        match_found = False
        for i in range(len(content)):
            line = content[i].strip()
            log.debug(line)
            pattern = r'' + variable + '=(.*)'
            # log.debug(pattern)
            match = re.match(pattern, line)
            if match is not None:
                log.debug(f'found {match.groups()}')
                content[i] = f'{variable}="{val}"\n'
                match_found = True
        if not match_found:
            # add to file
            content.append(f'{variable}="{val}"\n')
        if content is not None:
            with open(os.path.join(cwd, self.env_file), 'w') as f:
                f.writelines(content)
        
    def augment_env(self, key, value):
        self.env[key] = value


class ManifestsManager():

    @classmethod
    def get_upstream(cls, kf_version):
        # save current path
        cwd = os.getcwd()
        upstream_dir = os.path.join(cwd, 'upstream')
        if os.path.exists(upstream_dir):
            os.chdir(upstream_dir)
            tags = subprocess.check_output('git describe --tags', shell=True)
            current_version = tags.decode('utf-8').strip()
            log.info(f'Upstream for KubeFlow manifests version {current_version} found.')
            os.chdir(cwd)
            if current_version != kf_version:
                log.info('Version mismatch')
                shutil.rmtree(upstream_dir)
        if not os.path.exists(upstream_dir):
            log.info(f'Fetching KubeFlow {kf_version} ...')
            output = subprocess.check_output(f'git clone -c advice.detachedHead=false --branch {kf_version} \
                https://github.com/kubeflow/manifests.git --single-branch upstream', shell=True)
            log.info(output.decode('utf-8'))

    @classmethod
    def render_template(cls, env, template_file, rendered_path=None):
        cwd = os.getcwd()
        template_path = template_file.split('/')
        if rendered_path is None:
            rendered_path = re.sub(r'.tmpl', '', template_file).split('/')
            rendered_path_short = os.path.join(*rendered_path)
            rendered_path = os.path.join(cwd, *rendered_path)
        else:
            rendered_path_short = os.path.join(rendered_path)
        log.info(f'Created file: {rendered_path_short}')
        template = None
        with open(os.path.join(cwd, *template_path), 'r') as f:
            template = f.readlines()
        if template is not None:
            for i in range(len(template)):
                for env_var in env.keys():
                    val = env.get(env_var)
                    template[i] = re.sub(r'\$[{]?' + env_var + '[}]?', val, template[i])
                    template[i] = re.sub(r'\\\"', '"', template[i])
        for line in template:
            log.debug(f'                {line.rstrip()}')
        with open(rendered_path, 'w') as f:
            f.writelines(template)

    @classmethod
    def kustomize_manifests(cls, output_path):
        cwd = os.getcwd()
        overlay_path = os.path.join(cwd, 'deployments', 'overlays')
        if output_path is not None:
            log.debug(output_path)
            manifest_path = os.path.join(cwd, *output_path.split(os.sep))
            manifest_path_short = os.path.join(*output_path.split(os.sep))
            log.info(f'Generating manifests to {manifest_path_short}. This may take a few minutes...')
            cmd = f'kustomize build {overlay_path} -o {manifest_path}'
            run_shell_cmd(cmd)

    @classmethod
    def kustomize_and_apply(cls):
        cwd = os.getcwd()
        overlay_path = os.path.join(cwd, 'deployments', 'overlays')
        ready = False
        while not ready:
            try:
                log.info(f'Generating manifests and deploying. This may take a few minutes...')
                cmd = f'kustomize build {overlay_path}'.split()
                cmd2 = 'kubectl apply -f -'.split()
                log.debug(cmd)
                log.debug(cmd2)
                p = Popen(cmd, stdout=PIPE, stderr=PIPE)
                p2 = Popen(cmd2, stdin=p.stdout, stdout=PIPE, stderr=PIPE)
                while p2.poll() is None:
                    line = p2.stdout.readline()
                    log.info(line.decode('utf-8').rstrip())
                retcode = p.poll()
                if retcode == 0:
                    ready = True
            except Exception as e:
                log.error(e)


class AddOnManager():
    add_ons = None
    deferred_tasks = []
    final_tasks = []

    def __init__(self, env_manager):
        self.env_manager = env_manager
        self.get_add_ons()

    def get_add_ons(self):
        if self.add_ons is None:
            cwd = os.getcwd()
            self.add_ons = []
            with open(os.path.join(cwd, 'deployments', 'overlays', 'kustomization.yaml'), 'r') as f:
                add_ons_content = f.readlines()
                for line in add_ons_content:
                    line=line.strip()
                    if len(line) > 0 and line[0] != '#' and 'add-ons' in line:
                        add_on_name = line.split('/')[2]
                        self.add_ons.append(add_on_name)
            return self.add_ons

    def validate_addons_config(self):
        log.info('The following add-ons are defined in "./deployments/overlays/kustomization.yaml":')
        for add_on in self.add_ons:
            log.info(f'- {add_on}')
        log.warning('To disable add-ons that are not desired, comment them out in the kustomization.yaml file above.')
        log.info('Validating add-on configuration...')

        log.info(f'Checking configuration set in "{self.env_manager.env_file}":')
        for add_on in self.add_ons:
            log.info(f'- {add_on} add-on:')
            if add_on in add_on_variables.keys():
                variables_to_check = add_on_variables.get(add_on)
                log.debug(variables_to_check)
                for variable in variables_to_check:
                    specs = variable_specs.get(variable, {})
                    log.debug(specs)
                    self.env_manager.validate_env_variable(variable)
            else:
                log.warning(f'!!! {add_on} has no variables or is not recognized')
            log.info(f'  OK: variables are configured and matching patterns')

    def configure_add_ons(self):
        log.info('Configuring add-on templates...')
        self.deferred_tasks = []
        for add_on in self.add_ons:
            log.info(f'Add-on: {add_on}')
            if add_on == 'idcs':
                deferred = self.setup_idcs()
                if deferred:
                    self.deferred_tasks.append((self.setup_idcs, {}))
            elif add_on == 'letsencrypt-http01':
                self.setup_letsencrypt_http01()
            elif add_on == 'letsencrypt-dns01':
                domain_name = self.env_manager.env.get('OCI_KUBEFLOW_DOMAIN_NAME')
                dns_zone_compartment_id = self.env_manager.env.get('OCI_KUBEFLOW_DNS_ZONE_COMPARTMENT_OCID')
                InfrastructureManager.setup_dns_zone(domain_name, dns_zone_compartment_id)
                self.setup_letsencrypt_dns01()
                self.deferred_tasks.append((InfrastructureManager.setup_dns_records, {'domain_name': domain_name}))
                self.final_tasks.append((InfrastructureManager.get_dns_nameservers, {'domain_name': domain_name}))
            elif add_on == 'oci-object-storage':
                self.setup_oci_object_storage()
            elif add_on == 'external-mysql':
                self.setup_mysql()
        log.info('Add-ons are configured')
        log.debug(f'Deferred tasks: {self.deferred_tasks}')
        self.final_tasks.append((InfrastructureManager.get_lb_ip, {'verbose': True}))

    def setup_idcs(self):
        domain_name = self.env_manager.env.get('OCI_KUBEFLOW_DOMAIN_NAME', '')
        issuer = ''
        if domain_name == '':
            lb_ip = InfrastructureManager.get_lb_ip()
            if lb_ip == '':
                log.warning('Without setting up a domain name, IDCS can only be configured with the load balancer IP adress,')
                log.warning('however the IP is only available after deployment, so this process will be deferred')
            else:
                log.debug(f"Load Balancer IP: {lb_ip}")
            issuer = lb_ip
        else:
            issuer = domain_name
        env = self.env_manager.env
        if issuer == '':
            issuer = 'dex.auth.svc.cluster.local:5556'
            env['OCI_KUBEFLOW_ISSUER'] = f"http://{issuer}/dex"
            ManifestsManager.render_template(env, 'oci/common/dex/overlays/idcs/config.tmpl.yaml')
            ManifestsManager.render_template(env, 'oci/common/oidc-authservice/overlays/idcs/params.tmpl.env')
            return True # defer this action
        else:

            env['OCI_KUBEFLOW_ISSUER'] = f"https://{issuer}/dex"
            ManifestsManager.render_template(env, 'oci/common/dex/overlays/idcs/config.tmpl.yaml')
            ManifestsManager.render_template(env, 'oci/common/oidc-authservice/overlays/idcs/params.tmpl.env')
            return False

    def setup_letsencrypt_http01(self):
        env = self.env_manager.env
        ManifestsManager.render_template(env, 'oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-http01/kubeflow-gw.Certificate.tmpl.yaml')
        ManifestsManager.render_template(env, 'oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-http01/letsencrypt.ClusterIssuer.tmpl.yaml')
        ManifestsManager.render_template(env, 'oci/apps/kserve/domain/config-domain.tmpl.yaml')

    def setup_letsencrypt_dns01(self):
        env = self.env_manager.env
        ManifestsManager.render_template(env, 'oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-dns01/kubeflow-gw.Certificate.tmpl.yaml')
        ManifestsManager.render_template(env, 'oci/common/istio/kubeflow-istio-resources/overlays/letsencrypt-dns01/letsencrypt.ClusterIssuer.tmpl.yaml')
        ManifestsManager.render_template(env, 'oci/apps/kserve/domain/config-domain.tmpl.yaml')

    def setup_oci_object_storage(self):
        env = self.env_manager.env
        ManifestsManager.render_template(env, 'oci/apps/pipeline/oci-object-storage/config.tmpl')
        ManifestsManager.render_template(env, 'oci/apps/pipeline/oci-object-storage/minio.tmpl.env')
        ManifestsManager.render_template(env, 'oci/apps/pipeline/oci-object-storage/params.tmpl.env')

    def setup_mysql(self):
        env = self.env_manager.env
        ManifestsManager.render_template(env, 'oci/apps/pipeline/mds-external-mysql/mysql.tmpl.env')
        ManifestsManager.render_template(env, 'oci/apps/pipeline/mds-external-mysql/mysql.Service.tmpl.yaml')


class InfrastructureManager():

    @classmethod
    def get_lb_ip(cls, verbose=False):
        # Get load balancer IP
        cmd = 'kubectl get svc istio-ingressgateway -n istio-system -o=jsonpath="{.status.loadBalancer.ingress[0].ip}"'
        retry = 5
        while retry > 0:
            try:
                lb_ip=subprocess.check_output(cmd, shell=True).decode('utf-8')
            except subprocess.CalledProcessError as e:
                lb_ip=''
            if lb_ip == '':
                retry -= 1
                sleep(30)
            else:
                retry = 0
        if verbose:
            log.info(f'The load balancer IP is: {lb_ip} . Make sure to configure the A record with this IP at your domain name registrar.')
        return lb_ip

    @classmethod
    def setup_dns_zone(cls, domain_name, dns_zone_compartment_id):
        try:
            cmd = f'oci dns zone get --zone-name-or-id {domain_name}'
            subprocess.check_output(cmd, shell=True)
            log.info(f'DNS Zone is configured for domain "{domain_name}"')
        except subprocess.CalledProcessError:
            try:
                subprocess.check_output(f'oci dns zone create --compartment-id {dns_zone_compartment_id} --name {domain_name} --zone-type PRIMARY', shell=True)
                log.info(f'Please enter the nameservers above at the provider for the domain {domain_name}')
            except subprocess.CalledProcessError:
                log.error('Unable to create the DNS Zone. You may not have permission. Please try to create it manually.')
                exit(1)

    @classmethod
    def setup_dns_records(cls, domain_name):
        lb_ip = ''
        trial_count = 60  # try up to 10min
        while lb_ip == '' and trial_count > 0:
            lb_ip = cls.get_lb_ip()
            if lb_ip == '':
                sleep(10)
                trial_count -= 1
        if lb_ip == '':
            log.error('Could not retrieve Load Balancer IP adress')
            exit(1)        
        try:
            log.info(f'DNS setup: set A record with load balancer IP {lb_ip} for {domain_name}')
            # Set the A record pointing to the Load Balancer IP
            cmd = f'oci dns record rrset update --force --domain {domain_name} --zone-name-or-id {domain_name} --rtype "A" --items \'[{{"domain":"{domain_name}", "rdata":"{lb_ip}", "rtype": "A", "ttl":300}}]\''
            subprocess.check_output(cmd, shell=True)
        except subprocess.CalledProcessError:
            log.error('Unable to set load balancer IP on DNS. You may not have permission. Please try to set it up manually.')
            exit(1)
        try:
            log.info(f'DNS setup: set CNAME record for wildcard sub-domain *.{domain_name}')
            # Set the CNAME record pointing wildcard subdomains to the root domain
            cmd = f'oci dns record rrset update --force --domain "*.{domain_name}" --zone-name-or-id {domain_name} --rtype "CNAME" --items \'[{{"domain": "*.{domain_name}", "rdata": "{domain_name}", "rtype": "CNAME", "ttl":300}}]\''
            subprocess.check_output(cmd, shell=True)
        except subprocess.CalledProcessError:
            log.error('Unable to set CNAME record on DNS. You may not have permission. Please try to set it up manually.')
            exit(1)

    @classmethod
    def get_dns_nameservers(cls, domain_name):
        try:
            cmd = f'oci dns zone get --zone-name-or-id {domain_name}'
            subprocess.check_output(cmd, shell=True)
        except subprocess.CalledProcessError:
            log.error('Unable to get DNS Zone nameserver list. You may not have permission. Please try to set it up manually.')
            exit(1)

    @classmethod        
    def rollout_restart(cls):
        log.info('Restarting deployments...')
        for ns in ['kubeflow', 'auth', 'knative-serving', 'knative-eventing']:
            cmd = f'kubectl rollout restart deployments -n {ns}'
            run_shell_cmd(cmd)
        

class UserManager():

    def __init__(self):
        self.manifest_manager = ManifestsManager()

    def create(self, args):
        email = args.email
        while email == '':
            email = input('User Email:')
            log.debug(email)
            email = email.strip()
        username = args.username
        while username == '':
            username_default = re.sub(r'[@_.]', '-', email)
            username = input(f'Username/Namespace (defaults to {username_default}): ')
            username = username.strip()
            if username == '':
                username = username_default
        match = re.match(r'^[a-z0-9-]+$', username)
        log.debug(match)
        if match is None:
            log.error(f'username must comply with Kubernetes namespace naming pattern [a-z0-9-]+')
            exit(1)
        # check is namespace exists
        cmd = f'kubectl get ns {username}'.split()
        try:
            subprocess.check_output(cmd, shell=False)
            log.error(f'The username / namespace "{username}" already exists.')
            exit(1)
        except subprocess.CalledProcessError:
            pass
        env_vars = {
            'EMAIL': email,
            'USERNAME': username
        }
        cwd = os.getcwd()
        template_path = os.path.join(*['oci', 'profile', 'user-profile.tmpl.yaml'])
        rendered_path = os.path.join(cwd, *['oci', 'profile', f'{email}.Profile.yaml'])
        ManifestsManager.render_template(env_vars, template_path, rendered_path)
        cmd = f'kubectl apply -f {rendered_path}'
        run_shell_cmd(cmd)
        if args.kfp:
            kfp_template = os.path.join(cwd, *['oci', 'profile', 'pod_defaults', 'access-kf-pipeline.PodDefault.yaml'])
            cmd = f'kubectl apply -f {kfp_template} -n {username}'
            run_shell_cmd(cmd)


class MySQLManager():

    def __init__(self, env_manager=None):
        self.env_manager = env_manager

    def check_kf_user_login(self):
        user = self.env_manager.env.get('OCI_KUBEFLOW_MYSQL_USER')
        password = self.env_manager.env.get('OCI_KUBEFLOW_MYSQL_PASSWORD')
        mysql_host = self.env_manager.env.get('OCI_KUBEFLOW_MYSQL_HOST')
        overrides = '{ "apiVersion": "v1", "metadata": { "annotations": { "sidecar.istio.io/inject": "false" } } }'
        sql = f'"select 1;"'
        cmd = f'kubectl run mysql-set-kubeflow-user --rm -it --image=mysql:8.0.26 --restart=Never \
                --overrides=\'{overrides}\' -- mysql -u "{user}" -p"{password}" -h {mysql_host} \
                -e {sql} >/dev/null'
        log.debug(cmd.replace(password, '******'))
        return run_shell_cmd(cmd, shell=True, verbose=False) == 0

    def check_kf_user_exists_with_mysql_native_password(self, user, sys_user, sys_password, mysql_host):
        overrides = '{ "apiVersion": "v1", "metadata": { "annotations": { "sidecar.istio.io/inject": "false" } } }'
        sql = f'"select User, plugin from mysql.user where user = \'{user}\';"'
        cmd = f'kubectl run mysql-set-kubeflow-user --rm -it --image=mysql:8.0.26 --restart=Never \
                --overrides=\'{overrides}\' -- mysql -u "{sys_user}" -p"{sys_password}" -h {mysql_host} \
                -e {sql} | grep "| {user} | mysql_native_password |"'
        log.debug(cmd.replace(sys_password, '******'))
        return run_shell_cmd(cmd, shell=True, verbose=False) == 0
        
    def create_kf_user(self, args):
        user = args.user
        password = args.password
        sys_user = args.sys_user
        sys_password = args.sys_password
        mysql_host = args.mysql_host
        no_prompts = args.no_prompts
        if (password is None or sys_password is None) and no_prompts:
            if password is None:
                log.error('password is missing')
            if sys_password is None:
                log.error('sys-password is missing')
            exit(1)
        if not no_prompts:
            user = input(f'Enter username (defaults to "{user}"): ')
            if user.strip() == '':
                user = args.user
            else:
                user = user.strip()
        while not no_prompts and password is None:
            password = input(f'Enter a password for user "{user}": ')
            password = password.strip()
            if not self.env_manager.validate_pattern('OCI_KUBEFLOW_MYSQL_PASSWORD', password):
                password = None
        if not no_prompts:
            sys_user = input(f'Enter system/admin username (defaults to "{sys_user}"): ')
            if sys_user.strip() == '':
                sys_user = args.sys_user
            else:
                sys_user = sys_user.strip()
        if not no_prompts and sys_password is None:
            sys_password = input(f'Enter the password for the MySQL system/admin user "{sys_user}": ')
            sys_password = sys_password.strip()

        if not no_prompts:
            mysql_host = input(f'Enter the MySQL full host name (defaults to "{mysql_host}"): ')
            if mysql_host.strip() == '':
                mysql_host = args.mysql_host
            else:
                mysql_host = mysql_host.strip()

        if no_prompts is False:
            log.warning(f'This command will create a "{user}" user in the MySQL database.')
            log.warning(f'This command will update the environment variable "OCI_KUBEFLOW_MYSQL_USER" in the file "{self.env_manager.env_file}"')
            log.warning(f'This command will update the environment variable "OCI_KUBEFLOW_MYSQL_PASSWORD" in the file "{self.env_manager.env_file}"')
            log.warning(f'This command will update the environment variable "OCI_KUBEFLOW_MYSQL_HOST" in the file "{self.env_manager.env_file}"')
            log.warning('Would you like to continue? (y/N): ')
            choice = input('> ')
            if choice.lower().strip() != 'y':
                exit(0)

        if self.check_kf_user_exists_with_mysql_native_password(user, sys_user, sys_password, mysql_host):
            log.error(f'User "{user}" already exists')
            exit(1)

        overrides = '{ "apiVersion": "v1", "metadata": { "annotations": { "sidecar.istio.io/inject": "false" } } }'
        sql = f'"create user {user}@\'%\' identified with mysql_native_password by \'{password}\' default role administrator;"'
        cmd = f'kubectl run mysql-set-kubeflow-user --rm -it --image=mysql:8.0.26 --restart=Never \
                --overrides=\'{overrides}\' -- mysql -u "{sys_user}" -p"{sys_password}" -h {mysql_host} \
                -e {sql}'
        log.debug(cmd.replace(password, '******').replace(sys_password, '******'))
        if run_shell_cmd(cmd, shell=True, verbose=False) == 0:
            self.env_manager.save_variable('OCI_KUBEFLOW_MYSQL_USER', user)
            self.env_manager.save_variable('OCI_KUBEFLOW_MYSQL_PASSWORD', password)
            self.env_manager.save_variable('OCI_KUBEFLOW_MYSQL_HOST', mysql_host)
        else:
            log.error(f'User "{user}" could not be created. \
                Make sure the Security List in the VCN allow communication to the MySQL DB. \
                The user may exist already but does not use the "mysql_native_password" plugin. Try deleting the user and re-creating it.')

    def reset_db(self):
        cmds = [
            'kubectl apply -f reset-db.Job.yaml',
            'kubectl wait --for=condition=Complete --timeout=30s -n kubeflow job/reset-db',
            'kubectl logs job/reset-db',
            'kubectl rollout restart deployments -n kubeflow'
        ]
        for cmd in cmds:
            r = run_shell_cmd(cmd)
            if r != 0:
                log.error('command failed')
                exit(1)


class Configurator():

    env = None
    env_file=ENV_FILE
    no_prompts = False
    versions = None
    deferred_tasks = []
    env_manager = None
    addon_manager = None

    def __init__(self, args):

        if hasattr(args, 'env_file'):
            self.env_file = args.env_file
        if hasattr(args, 'no_prompts'):
            self.no_prompts = args.no_prompts
        else:
            self.no_prompts = True

    def configure(self):
        deps_validator = DependenciesValidator()
        deps_validator.validate_dependencies()
        kf_version = deps_validator.versions['KUBEFLOW_RELEASE_VERSION']
        ManifestsManager.get_upstream(kf_version)
        self.env_manager = EnvironmentManager(self.env_file, self.no_prompts)
        self.addon_manager = AddOnManager(self.env_manager)
        self.addon_manager.validate_addons_config()
        self.addon_manager.configure_add_ons()


class Main():

    def __init__(self):

        self.parser = argparse.ArgumentParser(description='OCI KubeFlow CLI',
                                        usage="./okf COMMAND [FLAGS]")
        self.subparsers = self.parser.add_subparsers(title='commands',
                                    description='valid subcommands',
                                    help="""
config: configure add-ons required variables and generate add-on manifests files.\n
build: configure add-ons and build manifests to file. Use if intermediate manifest files are needed.\n
deploy: configure, build manifests and deploy, without intermediate files.\n
user: manage user profiles.
mysql: manage mysql db
""")
        self.config_parser = self.subparsers.add_parser('config',
            usage='./okf config [FLAGS]',
            description="the config command configures the add-on manifests with the variables from the env-file")
        self.config_parser.add_argument('--yes', '-y', dest='no_prompts', help='no prompts. Will fails on missing values. Defaults to prompting for missing values', action='store_true')
        self.config_parser.add_argument('--env-file', '-e', dest="env_file", help='environment variables file to use (defaults to "kubeflow.env")', default=ENV_FILE)
        self.config_parser.set_defaults(func=self.config)
        
        self.build_parser = self.subparsers.add_parser('build', 
            usage='./okf build [FLAGS]',
            description="""
the build command is used to build manifests to file. It requires an output path or folder. 
Use -o <output file | folder> or use 'okf deploy' to build and deploy without intermediate files.
""")
        self.build_parser.add_argument('--output', '-o', help='output file or folder. If an existing folder is provided, generate individual manifests, as kustomize does.', required=True)
        self.build_parser.add_argument('--env_file', '-e', help='environment variables file to use (defaults to "kubeflow.env")', default=ENV_FILE)
        self.build_parser.set_defaults(func=self.build)

        self.deploy_parser = self.subparsers.add_parser('deploy', 
            usage='./okf deploy [FLAGS]',
            description="the deploy command configures add-ons, builds manifests and deploys.")
        self.deploy_parser.add_argument('--env-file', '-e', dest='env_file', help='environment variables file to use (defaults to "kubeflow.env")', default=ENV_FILE)
        self.deploy_parser.add_argument('--no-restart', '-n', dest='no_restart', help='disable forced rollout restart of the deployment to insure istio-sidecars are activated.', action='store_true', default=False)
        self.deploy_parser.set_defaults(func=self.deploy)

        self.user_parser = self.subparsers.add_parser('user', usage="./okf user COMMAND", 
                    description='the user command provides utilities to manage user namespaces.')
        self.user_parser.set_defaults(func=self.user)

        self.user_subparsers = self.user_parser.add_subparsers(title='subcommands',
                                    description='valid subcommands',
                                    help='see each command\'s help for additional help')

        self.user_create_parser = self.user_subparsers.add_parser('create', 
                usage="okf user create -E email -U username")
        self.user_create_parser.add_argument('--email', '-E', dest='email', help='user email', default='')
        self.user_create_parser.add_argument('--username', '-U', help='username', default='')
        self.user_create_parser.add_argument('--kpf', dest='kfp', help='enable access to KubeFlow Pipelines in notebooks', action='store_true', default=False)
        self.user_create_parser.set_defaults(func=self.user_create)

        self.mysql_parser = self.subparsers.add_parser('mysql', 
            usage="./okf mysql COMMAND", 
            description='the mysql command provides utilities to manage the mysql database.')
        self.mysql_parser.set_defaults(func=self.mysql)

        self.mysql_subparsers = self.mysql_parser.add_subparsers(title='subcommands',
                                    description='valid subcommands',
                                    help='see each command\'s help for additional help')

        self.mysql_create_kf_user_parser = self.mysql_subparsers.add_parser('create-kf-user', usage="okf mysql create-kf-user")
        self.mysql_create_kf_user_parser.add_argument('--env_file', '-e', help='environment variables file to use (defaults to "kubeflow.env")', default=ENV_FILE)
        self.mysql_create_kf_user_parser.add_argument('--user', '-u', dest='user', help='user name', default='kubeflow')
        self.mysql_create_kf_user_parser.add_argument('--password', '-p', dest='password', help='user password', default=None)
        self.mysql_create_kf_user_parser.add_argument('--sys-user', '-U', dest='sys_user', help='sys/admin username', default='ADMIN')
        self.mysql_create_kf_user_parser.add_argument('--sys-password', '-P', dest='sys_password', help='sys/admin password', default=None)
        self.mysql_create_kf_user_parser.add_argument('--mysql-host', '-H', dest='mysql_host', help='mysql host', default=None)
        self.mysql_create_kf_user_parser.add_argument('--yes', '-y', dest='no_prompts', help='no prompts', action='store_true')
        self.mysql_create_kf_user_parser.set_defaults(func=self.mysql_create_kf_user)

        self.mysql_reset_db_parser = self.mysql_subparsers.add_parser('reset-db', usage="okf mysql reset-db", description="resets the metada, cache and mlpipeline tables")
        self.mysql_reset_db_parser.set_defaults(func=self.mysql_reset_db)

        args = self.parser.parse_args()
        debug = os.environ.get('DEBUG', None)
        log_level = logging.DEBUG if debug is not None else logging.INFO
        log.setLevel(log_level)

        if hasattr(args, 'func'):
            args.func(args)
        else:
            self.parser.print_help()

    def config(self, args):
        log.debug(args)
        cfg = Configurator(args)
        cfg.configure()
        log.debug(cfg.env_manager.env)
        return cfg

    def build(self, args):
        log.debug(args)
        cfg = self.config(args)
        try:
            output_dest = args.output
        except AttributeError:
            output_dest = None
        if output_dest is not None:
            ManifestsManager.kustomize_manifests(output_dest)
        return cfg


    def deploy(self, args):
        log.debug(args)
        cfg = self.build(args)
        if 'external-mysql' in cfg.addon_manager.add_ons:
            env_manager = EnvironmentManager(args.env_file)
            mysql_manager = MySQLManager(env_manager)
            if not mysql_manager.check_kf_user_login():
                log.error('The KubeFlow user cannot login with the credentials defined.')
                log.warning('use "./okf mysql create-kf-user" to create the KubeFlow user, or check it was properly created and credentials defined in the env_file are valid.')
                exit(1)
        ManifestsManager.kustomize_and_apply()
        log.debug(f'calling deferred tasks {cfg.deferred_tasks}')
        for func, func_args in cfg.addon_manager.deferred_tasks:
            log.debug(f"calling {func} with {func_args}")
            func(*func_args)
        log.debug(args.no_restart)
        if not args.no_restart:
            InfrastructureManager.rollout_restart()
        for func, func_args in cfg.addon_manager.final_tasks:
            log.debug(f"calling {func} with {func_args}")
            func(*func_args)

    def user(self, args):
        log.debug(args)
        self.user_parser.print_help()


    def user_create(self, args):
        um = UserManager()
        um.create(args)


    def mysql(self, args):
        log.debug(args)
        self.mysql_parser.print_help()


    def mysql_create_kf_user(self, args):
        env_file = args.env_file
        env_manager = EnvironmentManager(env_file)
        mysql_manager = MySQLManager(env_manager)
        mysql_manager.create_kf_user(args)


    def mysql_reset_db(self, args):
        mysql_manager = MySQLManager()
        mysql_manager.reset_db()


if __name__ == '__main__':
    Main()