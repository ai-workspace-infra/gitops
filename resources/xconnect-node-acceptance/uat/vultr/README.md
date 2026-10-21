# Isolated Vultr acceptance declaration

Infrastructure declaration: node-20261021.yaml, consumed only by the dedicated
IaC workspace/state. Do not pass this whole directory to the infrastructure
renderer: node-profiles.yaml and acceptance-domains.yaml are service contracts.

Selected deployment naming: ENV=sit, DEPLOYMENT_ID=v4, DOMAIN_BASE supplied
explicitly. The UAT directory names the provisioning account/state boundary;
the isolated SIT application naming does not alter that backend identity.

2026-10-21: one new instance and one 25 GB high_perf data volume created via
Terraform. Provider facts: 2 vCPU/2048 MB/65 GB root, Tokyo, public IPv4.
Dedicated state key: uat/xconnect-node-acceptance/20261021/terraform.tfstate.
Retain state and CMDB for audit and explicit later cleanup. Existing environments
were not modified. DNS and full application deployment remain pending.

node-profiles.yaml records fixed artifact candidates and explicit missing gates;
it is not an executable release manifest. deployment_ready remains false until
native profile deployment and isolated controller evidence exist. No production
token or team identity is provisioned by this declaration.
