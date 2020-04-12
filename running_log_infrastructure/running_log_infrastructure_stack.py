from aws_cdk import (core, aws_ec2 as ec2, aws_ecs as ecs, aws_ecr as ecr,
                     aws_ecs_patterns as ecs_patterns, aws_rds as rds,
                     aws_secretsmanager as secretsmanager)


class RunningLogInfrastructureStack(core.Stack):

    FLASK_SECRET_ARN = "arn:aws:secretsmanager:us-east-2:412703736941:secret:running-log/flask-6NPAP2"

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc(self, "RunningLogVPC", max_azs=3)  # default is all AZs in region

        sg = ec2.SecurityGroup(self, "RunningLogAuroraSG",
                               vpc=vpc,
                               allow_all_outbound=True,
                               description="Aurora Security Group"
                               )
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(3306), "Aurora")

        rds_cluster_params = rds.ClusterParameterGroup.from_parameter_group_name(self, 'ParameterGroup',
                                                                                 "default.aurora-mysql5.7")
        db = rds.DatabaseCluster(self, "RunningLogMySQL",
                                 cluster_identifier="running-log",
                                 default_database_name="db",
                                 engine=rds.DatabaseClusterEngine.AURORA_MYSQL,
                                 engine_version="5.7.mysql_aurora.2.07.2",
                                 instance_props=rds.InstanceProps(
                                     instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3,
                                                                       ec2.InstanceSize.SMALL),
                                     vpc_subnets=ec2.SubnetSelection(
                                         subnet_type=ec2.SubnetType.PUBLIC
                                     ),
                                     security_group=sg,
                                     vpc=vpc
                                 ),
                                 instances=1,
                                 master_user=rds.Login(username="erin"),
                                 parameter_group=rds_cluster_params
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
                                                           cpu=512,
                                                           desired_count=1,
                                                           task_image_options=alb_task_options,
                                                           memory_limit_mib=2048,
                                                           public_load_balancer=True
                                                           )
