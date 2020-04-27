# Migrating from using EGI ActiveMQ Message Brokers to using EGI ARGO Messaging Service

Migration requires upgrading SSM to at least version 2.4.0 and adding new values to your configuration.

## Sender

The sender configuration is usually found under `/etc/apel/sender.cfg`. Follow the steps below to migrate.

1. Comment out `bdii` and `network`.
1. Uncomment `host` and set it to `msg-devel.argo.grnet.gr`.
1. Add the following as a new section at the top of your configuration:
```
[sender]
# Either 'STOMP' for STOMP message brokers or 'AMS' for Argo Messaging Service
protocol: AMS
```
1. Add the following to the `[messaging]` section of your configuration:
```
# If using AMS this is the project that SSM will connect to. Ignored for STOMP.
ams_project: accounting
```
1. To send to the central APEL Accounting server, change `destination` to one of the following depending on your type of accounting:
  * `gLite-APEL` for Grid Accounting
  * `eu.egi.cloud.accounting` for Cloud Accounting
  * `eu.egi.storage.accounting` for Storage Accounting

The next time `ssmsend` runs it should be using the AMS. You can check this by looking in the logs for a successful run, which should look like this:

```
2018-09-19 14:18:06,423 - ssmsend - INFO - ========================================
2018-09-19 14:18:06,424 - ssmsend - INFO - Starting sending SSM version 2.4.0.
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

1. Follow the steps 1 to 4 as per the [Sender documentation](#Sender) but editing your receiver configuration instead, usually found under `/etc/apel/receiver.cfg`, naming the sction `[receiver]` rather than `[sender]`.
1. Change `destination` to be the subscription you are using to pull messages down.
1. Add your token to the `[messaging]` section of your configuration:
```
token: your_token_here
```
