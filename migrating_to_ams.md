# Migrating from using EGI ActiveMQ Message Brokers to using EGI ARGO Messaging Service

## Prerequisites for using AMS

- A valid host certificate from an IGTF Accredited CA.
- A GOCDB 'Site' entry flagged as 'Production'.
- A GOCDB 'Service' entry of the correct service type flagged as 'Production'. The following service types are used:
  - For Grid accounting use 'gLite-APEL'.
  - For Cloud accounting use 'eu.egi.cloud.accounting'.
  - For Storage accounting use 'eu.egi.storage.accounting'.
- The 'Host DN' listed in the GOCDB 'Service' entry must exactly match the certificate DN of the host used for accounting. Make sure there are no leading or trailing spaces in the 'Host DN' field.
- Messages sent via AMS must be below 1 Megabyte in size, and the messaging service is optimised around this limit. If your messages start hitting this limit when using SSM, see the advice at the bottom of this document.

## Software requirements

Migration requires upgrading APEL SSM to at least version 2.4.0, installing the ARGO AMS Library, and adding new values to your configuration.

The ARGO AMS Library is available in UMD as `python-argo-ams-library`. Versions above 0.5.0 are recommended.

## Configuration changes

### Sender

The sender configuration is usually found under `/etc/apel/sender.cfg`. Follow the steps below to migrate.

1. Comment out `bdii` and `network`.
1. Uncomment `host` and set it to `msg.argo.grnet.gr`.
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
   * `eu-egi-cloud-accounting` for Cloud Accounting
   * `eu-egi-storage-accounting` for Storage Accounting

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

### Receiver

This is only used for the central Accounting Repository, Accounting Portal, and regional accounting servers.

1. Follow the steps 1 to 4 as per the [Sender documentation](#Sender) but editing your receiver configuration instead, usually found under `/etc/apel/receiver.cfg`, naming the section `[receiver]` rather than `[sender]`.
1. Change `destination` to be the subscription you are using to pull messages down.
1. Add your token to the `[messaging]` section of your configuration:
   ```
   token: your_token_here
   ```

## Issues

### Messages too large

- Cloud sites using cASO should ensure they are using at least version 1.4.0 of cASO as this version limits the number of records in a message.
- Grid sites using the APEL accounting client need to be using APEL 1.9.0 and SSM 3.2.0. They can then modify their APEL client script, usually located at `/usr/bin/apelclient`. At the moment, this requires a manual change, but will become a configuration option in the next version of APEL. For example, to halve the number of records per message from the default of 1000, add the line `unloader.records_per_message = 500` after the call to `DbUnloader`:
  ```
  @@ -233,6 +233,7 @@ def run_client(ccp):

           unloader = DbUnloader(db, unload_dir, include_vos, exclude_vos,
                                 local_jobs, withhold_dns)
  +        unloader.records_per_message = 500
           try:
               if interval == 'latest':
                   msgs, recs = unloader.unload_latest(table_name, send_ur)
  ```
