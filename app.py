#!/usr/bin/env python3

from aws_cdk import core

from running_log_infrastructure.running_log_infrastructure_stack import RunningLogInfrastructureStack


app = core.App()
RunningLogInfrastructureStack(app, "running-log-prod")

app.synth()
