/**
 * MIT License
 *
 * Copyright (c) 2025 VeloSim Contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import path from 'path';

export interface VeloSimStackProps extends cdk.StackProps {
  // Configuration options
  allowedIpAddresses?: string[]; // IP addresses allowed to access the app
  mapboxAccessToken?: string; // Optional: Mapbox token for frontend
}

export class VeloSimStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: VeloSimStackProps) {
    super(scope, id, props);

    // Get allowed IPs from context or props (you'll set these during deployment)
    let allowedIps: string | string[] = props?.allowedIpAddresses ||
      this.node.tryGetContext('allowedIps') ||
      ['0.0.0.0/0']; // Default: open to all (change this!)
    if (typeof allowedIps === 'string') {
      allowedIps = allowedIps.split(',')
    }

    // ============================================================================
    // VPC
    // ============================================================================
    const vpc = new ec2.Vpc(this, 'VeloSimVPC', {
      maxAzs: 2,
      natGateways: 0, // No NAT gateway to save costs
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
        },
      ],
    });

    // ============================================================================
    // RDS PostgreSQL Database
    // ============================================================================

    // Security group for RDS
    const dbSecurityGroup = new ec2.SecurityGroup(this, 'DatabaseSecurityGroup', {
      vpc,
      description: 'Security group for VeloSim RDS database',
      allowAllOutbound: false,
    });

    // Generate database credentials
    const dbCredentials = new secretsmanager.Secret(this, 'DBCredentials', {
      secretName: 'velosim/db-credentials',
      generateSecretString: {
        secretStringTemplate: JSON.stringify({ username: 'velosim' }),
        generateStringKey: 'password',
        excludePunctuation: true,
        includeSpace: false,
        passwordLength: 32,
      },
    });

    // RDS PostgreSQL instance
    const database = new rds.DatabaseInstance(this, 'VeloSimDatabase', {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_15,
      }),
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.T4G,
        ec2.InstanceSize.MICRO
      ),
      credentials: rds.Credentials.fromSecret(dbCredentials),
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC, // Public subnet to avoid NAT gateway
      },
      securityGroups: [dbSecurityGroup],
      allocatedStorage: 20,
      storageType: rds.StorageType.GP3,
      databaseName: 'velosim',
      backupRetention: cdk.Duration.days(7),
      deleteAutomatedBackups: true,
      removalPolicy: cdk.RemovalPolicy.SNAPSHOT, // Take snapshot on delete
      publiclyAccessible: false, // Only accessible from within VPC
      multiAz: false, // Single AZ to save costs
    });

    // ============================================================================
    // ECR Repository for Docker Images
    // ============================================================================

    const ecrRepository = new ecr.Repository(this, 'VeloSimRepository', {
      repositoryName: 'velosim',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lifecycleRules: [
        {
          description: 'Keep last 10 images',
          maxImageCount: 10,
        },
      ],
    });

    // ============================================================================
    // ECS Cluster
    // ============================================================================

    const cluster = new ecs.Cluster(this, 'VeloSimCluster', {
      vpc,
      clusterName: 'velosim-cluster',
      enableFargateCapacityProviders: false,
    });

    // ============================================================================
    // IAM Role for ECS EC2 Instances
    // ============================================================================

    const ecsInstanceRole = new iam.Role(this, 'ECSInstanceRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonEC2ContainerServiceforEC2Role'),
      ],
    });

    // Create instance profile
    const instanceProfile = new iam.CfnInstanceProfile(this, 'ECSInstanceProfile', {
      roles: [ecsInstanceRole.roleName],
    });

    // ============================================================================
    // ECS Task Definition
    // ============================================================================

    const taskDefinition = new ecs.Ec2TaskDefinition(this, 'VeloSimTaskDef', {
      networkMode: ecs.NetworkMode.HOST,
    });

    // CloudWatch Log Group for application logs
    const logGroup = new logs.LogGroup(this, 'VeloSimLogGroup', {
      logGroupName: '/ecs/velosim',
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Backend container
    const backendContainer = taskDefinition.addContainer('backend', {
      image: ecs.ContainerImage.fromEcrRepository(ecrRepository, 'latest'),
      memoryLimitMiB: 1536, // 1.5GB for backend
      cpu: 1536,
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'backend',
        logGroup,
      }),
      environment: {
        ENVIRONMENT: 'production',
        DEBUG: 'false',
        ALLOWED_ORIGINS: '["*"]', // Will be updated with actual frontend URL
        DB_HOST: database.dbInstanceEndpointAddress,
        DB_PORT: database.dbInstanceEndpointPort,
        DB_NAME: 'velosim',
      },
      secrets: {
        DB_USERNAME: ecs.Secret.fromSecretsManager(dbCredentials, 'username'),
        DB_PASSWORD: ecs.Secret.fromSecretsManager(dbCredentials, 'password'),
      },
    });

    backendContainer.addPortMappings({
      containerPort: 8000,
      hostPort: 8000,
      protocol: ecs.Protocol.TCP,
    });

    // Frontend container (in same task for simplicity)
    const frontendContainer = taskDefinition.addContainer('frontend', {
      image: ecs.ContainerImage.fromEcrRepository(ecrRepository, 'frontend-latest'),
      memoryLimitMiB: 512, // 512MB for frontend
      cpu: 512,
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'frontend',
        logGroup,
      }),
      environment: {
        VITE_BACKEND_URL: 'http://35.183.9.20', // Update after deployment to frontend IP
        VITE_MAPBOX_ACCESS_TOKEN: props?.mapboxAccessToken || '',
      },
    });

    frontendContainer.addPortMappings({
      containerPort: 3000,
      hostPort: 3000,
      protocol: ecs.Protocol.TCP,
    });

    const proxyImage = ecs.ContainerImage.fromAsset(
      path.join(__dirname, '..', '..', 'docker', 'nginx-proxy'),
    );

    const proxyContainer = taskDefinition.addContainer('proxy', {
      image: proxyImage,
      essential: true,
      memoryReservationMiB: 64,
      logging: ecs.LogDrivers.awsLogs({ streamPrefix: 'proxy' }),
    });

    proxyContainer.addPortMappings({
      containerPort: 80,
      hostPort: 80,
      protocol: ecs.Protocol.TCP,
    });

    // Start proxy after app containers to reduce race during bootstrap
    proxyContainer.addContainerDependencies(
      {
        container: backendContainer,
        condition: ecs.ContainerDependencyCondition.START,
      },
      {
        container: frontendContainer,
        condition: ecs.ContainerDependencyCondition.START,
      },
    );

    // ============================================================================
    // EC2 Instance for ECS
    // ============================================================================

    // Security group for ECS instances
    const ecsSecurityGroup = new ec2.SecurityGroup(this, 'ECSSecurityGroup', {
      vpc,
      description: 'Security group for VeloSim ECS instances',
      allowAllOutbound: true,
    });

    // Allow HTTP access from specified IPs only
    allowedIps.forEach((ip: string) => {
      ecsSecurityGroup.addIngressRule(
        ec2.Peer.ipv4(ip),
        ec2.Port.tcp(80),
        `Allow HTTP from ${ip}`
      );
    });

    // Allow database access from ECS
    dbSecurityGroup.addIngressRule(
      ecsSecurityGroup,
      ec2.Port.tcp(5432),
      'Allow PostgreSQL access from ECS'
    );

        // Create user data for ECS configuration
    const userData = ec2.UserData.forLinux();
    userData.addCommands(
      `echo ECS_CLUSTER=${cluster.clusterName} >> /etc/ecs/ecs.config`
    );

    // Create Launch Template for ECS instances
    const launchTemplate = new ec2.LaunchTemplate(this, 'ECSLaunchTemplate', {
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.T4G,
        ec2.InstanceSize.MEDIUM
      ),
      machineImage: ecs.EcsOptimizedImage.amazonLinux2(ecs.AmiHardwareType.ARM),
      securityGroup: ecsSecurityGroup,
      userData: userData,
      role: ecsInstanceRole,
      requireImdsv2: true, // Best practice for security
    });

    // Auto Scaling Group for EC2 instances
    const autoScalingGroup = new cdk.aws_autoscaling.AutoScalingGroup(this, 'ECSAutoScalingGroup', {
      vpc,
      launchTemplate: launchTemplate,
      minCapacity: 1,
      maxCapacity: 1,
      desiredCapacity: 1,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
    });

    // Add capacity to ECS cluster
    const capacityProvider = new ecs.AsgCapacityProvider(this, 'AsgCapacityProvider', {
      autoScalingGroup,
      enableManagedTerminationProtection: false,
    });

    cluster.addAsgCapacityProvider(capacityProvider);

    // ============================================================================
    // ECS Service
    // ============================================================================

    const service = new ecs.Ec2Service(this, 'VeloSimService', {
      cluster,
      taskDefinition,
      desiredCount: 1, // On first deploy, set to zero to avoid image-pull race
      capacityProviderStrategies: [
        {
          capacityProvider: capacityProvider.capacityProviderName,
          weight: 1,
        },
      ],
    });

    // ============================================================================
    // Migration Task Definition
    // ============================================================================

    const migrationTaskDefinition = new ecs.Ec2TaskDefinition(this, 'VeloSimMigrationTaskDef', {
      networkMode: ecs.NetworkMode.BRIDGE,
      family: 'velosim-migration',
    });

    // CloudWatch Log Group for migration logs
    const migrationLogGroup = new logs.LogGroup(this, 'VeloSimMigrationLogGroup', {
      logGroupName: '/ecs/velosim-migrations',
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const migrationContainer = migrationTaskDefinition.addContainer('migrations', {
      image: ecs.ContainerImage.fromEcrRepository(ecrRepository, 'latest'),
      logging: ecs.LogDrivers.awsLogs({ streamPrefix: 'migrations', logGroup }),
      memoryLimitMiB: 512,
      environment: {
        DB_HOST: database.dbInstanceEndpointAddress,
        DB_PORT: database.dbInstanceEndpointPort,
        DB_NAME: 'velosim',
        ENVIRONMENT: 'production',
        DEBUG: 'false',
      },
      secrets: {
        DB_USERNAME: ecs.Secret.fromSecretsManager(dbCredentials, 'username'),
        DB_PASSWORD: ecs.Secret.fromSecretsManager(dbCredentials, 'password'),
      },
      // Run in /app/back so alembic.ini is picked up automatically
      workingDirectory: '/app/back',
      command: ['alembic', 'upgrade', 'head'],
    });

    // ============================================================================
    // IAM Permissions for GitHub Actions
    // ============================================================================

    // Create IAM user for GitHub Actions (you can also use OIDC instead)
    const githubActionsUser = new iam.User(this, 'GitHubActionsUser', {
      userName: 'velosim-github-actions',
    });

    // Grant permissions to push to ECR
    ecrRepository.grantPullPush(githubActionsUser);

    // Grant permissions to update ECS service
    githubActionsUser.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'ecs:UpdateService',
          'ecs:DescribeServices',
          'ecs:DescribeTaskDefinition',
          'ecs:RegisterTaskDefinition',
          'ecs:RunTask',
          'ecs:DescribeTasks',
        ],
        resources: ['*'],
      })
    );

    // Grant permissions to pass IAM roles to ECS
    githubActionsUser.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['iam:PassRole'],
        resources: [
          taskDefinition.taskRole.roleArn,
          taskDefinition.executionRole!.roleArn,
          migrationTaskDefinition.taskRole.roleArn,
          migrationTaskDefinition.executionRole!.roleArn,
        ],
      })
    );

    // Grant permissions to read secrets for migrations
    dbCredentials.grantRead(githubActionsUser);

    // Create access key for GitHub Actions
    const accessKey = new iam.CfnAccessKey(this, 'GitHubActionsAccessKey', {
      userName: githubActionsUser.userName,
    });

    // ============================================================================
    // Outputs
    // ============================================================================

    new cdk.CfnOutput(this, 'ECRRepositoryURI', {
      value: ecrRepository.repositoryUri,
      description: 'ECR Repository URI for Docker images',
    });

    new cdk.CfnOutput(this, 'DatabaseEndpoint', {
      value: database.dbInstanceEndpointAddress,
      description: 'RDS Database endpoint',
    });

    new cdk.CfnOutput(this, 'DatabaseSecretArn', {
      value: dbCredentials.secretArn,
      description: 'ARN of the database credentials secret',
    });

    new cdk.CfnOutput(this, 'ECSClusterName', {
      value: cluster.clusterName,
      description: 'ECS Cluster name',
    });

    new cdk.CfnOutput(this, 'ECSServiceName', {
      value: service.serviceName,
      description: 'ECS Service name',
    });

    new cdk.CfnOutput(this, 'MigrationTaskDefinitionFamily', {
      value: migrationTaskDefinition.family,
      description: 'Migration task definition family name',
    });

    new cdk.CfnOutput(this, 'GitHubActionsAccessKeyId', {
      value: accessKey.ref,
      description: 'Access Key ID for GitHub Actions',
    });

    new cdk.CfnOutput(this, 'GitHubActionsSecretAccessKey', {
      value: accessKey.attrSecretAccessKey,
      description: 'Secret Access Key for GitHub Actions (store securely!)',
    });

    new cdk.CfnOutput(this, 'AutoScalingGroupName', {
      value: autoScalingGroup.autoScalingGroupName,
      description: 'Auto Scaling Group name (use to find EC2 instance public IP)',
    });
  }
}
