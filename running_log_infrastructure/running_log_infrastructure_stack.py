from aws_cdk import (core, aws_ec2 as ec2, aws_ecs as ecs, aws_ecr as ecr,
                     aws_ecs_patterns as ecs_patterns, aws_rds as rds,
                     aws_secretsmanager as secretsmanager)


class RunningLogInfrastructureStack(core.Stack):

    FLASK_SECRET_ARN = "arn:aws:secretsmanager:us-east-2:412703736941:secret:running-log/flask-6NPAP2"

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc(self, "RunningLogVPC",
                      max_azs=2,
                      nat_gateways=0,  # CREATES ONE NAT GATEWAY ($1 a day) PER AZ BY DEFAULT! WTH
                      subnet_configuration=[
                          ec2.SubnetConfiguration(
                              name="Public",
                              subnet_type=ec2.SubnetType.PUBLIC
                          )]
                      )

        sg = ec2.SecurityGroup(self, "RunningLogMySQLSG",
                               vpc=vpc,
                               allow_all_outbound=True,
                               description="MySQL Security Group"
                               )
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(3306), "MySQL")

        db = rds.DatabaseInstance(self, "RunningLogMysql",
                                  engine=rds.DatabaseInstanceEngine.MYSQL,
                                  engine_version="5.7.28",
                                  instance_class=ec2.InstanceType('t3.micro'),
                                  vpc=vpc,
                                  vpc_placement=ec2.SubnetSelection(
                                      subnet_type=ec2.SubnetType.PUBLIC
                                  ),
                                  security_groups=[sg],
                                  master_username="erin",
                                  deletion_protection=False
                                  )

        cluster = ecs.Cluster(self, "RunningLogCluster", vpc=vpc, cluster_name="running-log")

        flask_secret = secretsmanager.Secret.from_secret_arn(self, "RunningLogFlask",
                                                             RunningLogInfrastructureStack.FLASK_SECRET_ARN)

        alb_task_options = ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
            container_name="running-log",
            secrets={
                "AURORA_CREDS": ecs.Secret.from_secrets_manager(db.secret),
                "FLASK_SECRET": ecs.Secret.from_secrets_manager(flask_secret)
            },
            image=ecs.ContainerImage.from_ecr_repository(ecr.Repository.from_repository_name(
                self, "RunningLogRepo", repository_name="running-log")
            )
        )

        ecs_patterns.ApplicationLoadBalancedFargateService(self, "RunningLogService",
                                                           cluster=cluster,
                                                           cpu=256,
                                                           desired_count=2,
                                                           task_image_options=alb_task_options,
                                                           memory_limit_mib=1024,
                                                           public_load_balancer=True,
                                                           assign_public_ip=True
                                                           )
