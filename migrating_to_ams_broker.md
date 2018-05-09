# Migrating from using EGI ActiveMQ Message Brokers to using EGI ARGO Messaging Service

Migration requires upgrading to SSM-X.X.X and adding new values to your configuration.

## Sender

The sender configuration is usually found under `/etc/apel/sender.cfg`. Follow the following steps to migrate.

1. Comment out `bdii` and `network`
2. Uncomment `host` and set it to `msg-devel.argo.grnet.gr`
3. Add the following as a new section in your configuration.
```
# SSM protocol/destination type options
[SSM Type]
# Either 'MQ-BROKER' for EGI Message Brokers or 'AMS' for Argo Messaging Service
destination type: AMS
# Either 'STOMP' for EGI Message Brokers or 'HTTPS' for Argo Messaging Service
protocol: HTTPS
```
4. Add the following to the `[messaging]` section of your configuration
```
# Project to which SSM will pull messages from. Uncomment and populate for AMS sending
project: EGI-ACCOUNTING
```
5. To send to the APEL central server, change `destination` to one of the following depending on your type of accounting:
  * `gLite-APEL` for Grid Accounting
  * `eu.egi.cloud.accounting` for Cloud Accounting
  * `eu.egi.storage.accounting` for Storage Accounting

The next time `ssmsend` runs it should be using the AMS. You can check this by looking in the logs a successful run, which will look like:
```
2018-09-19 14:18:06,423 - ssmsend - INFO - ========================================
2018-09-19 14:18:06,424 - ssmsend - INFO - Starting sending SSM version 2.2.1.
2018-09-19 14:18:06,424 - ssmsend - INFO - Setting up SSM with Dest Type: AMS, Protocol : HTTPS
2018-09-19 14:18:06,424 - ssmsend - INFO - No AMS token provided, using cert/key pair instead.
2018-09-19 14:18:06,424 - ssmsend - INFO - No server certificate supplied.  Will not encrypt messages.
2018-09-19 14:18:07,061 - ssm.ssm2 - INFO - Found 1 messages.
2018-09-19 14:18:07,860 - ssm.ssm2 - INFO - Sent 5ba24c88/5ba24c8f0f129d, Argo ID: 18
2018-09-19 14:18:07,861 - ssm.ssm2 - INFO - Tidying message directory.
2018-09-19 14:18:07,862 - ssmsend - INFO - SSM run has finished.
2018-09-19 14:18:07,862 - ssmsend - INFO - SSM has shut down.
2018-09-19 14:18:07,862 - ssmsend - INFO - ========================================
```

## Receiver
1. Follow the steps 1 to 4 from above editing your receiver configuration, usually found under `/etc/apel/receiver.cfg`
2. Change `destination` to be the subscription you are using to pull messages down.
3. Add your token to the `[messaging]` section of your configuration.
```
token: your_token_here
```
