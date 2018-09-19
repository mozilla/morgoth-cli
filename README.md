# morgoth-cli
A command line tool to help with shipping system addons in Balrog

### Installation

Clone the repo locally:

```
$ git clone https://github.com/rehandalal/morgoth-cli.git
```

Use pip to install from the repo:

```
$ cd morgoth-cli
$ pip install --editable .
```

***Note:** You can leave out the `--editable` flag however you will
then need to reinstall any time you update the repo.*

### Configuration

To configure this tool simply run the following command:

```
$ morgoth init
```

***Note:** This command validates your authentication credentials and
you will need to be connected to the VPN to successfully run it.*

If you change your password/credentials at any point you can use 
the `auth` command to make changes to your auth settings:

```
$ morgoth auth
```

Additionally if you need to change any other configurations you
can simply run:

```
$ morgoth config [KEY] [VALUE]
```

For example if you use AWS profile you can configure the profile
to use with the following:

```
$ morgoth config aws.profile my-profile-name
```

#### Configuration options

`balrog_url`: The URL of the Balrog server to use.

`username`: Your LDAP username.

`password`: Your LDAP password. (Encrypted using GPG before it 
is stored)

`gpg.homedir`: The GPG homedir where your keys are stored.

`gpg.fingerprint`: The fingerprint of the GPG key you would like 
to use for encryption.

`aws.profile`: The name of the AWS profile to use.

`aws.prefix`: The prefix to be added to the filename in the S3 bucket.

`aws.bucket_name`: The name of the S3 bucket to use.

`aws.base_url`: The base public URL for the S3 bucket.


### Usage

##### Make releases:

```
$ morgoth make release [PATH_TO_XPI]
```

This command is used to create a new release from an XPI file. It will 
check if the XPI has been uploaded to S3 and if not upload it for you 
with the correctly formatted file name.

It will then give you the option to directly upload the release to 
Balrog, or save it to a file, or simply output it to stdout.

##### Make superblobs:

```
$ morgoth make superblob [RELEASES] 
```

A superblob is a type of release that represents a group of releases.

The releases passed to this command may either be the name of a release
or the path to a JSON file with the data for a release.

It will then give you the option to directly upload the release to 
Balrog, or save it to a file, or simply output it to stdout.

##### Modify rules:

```
$ morgoth modify rules [RULES]
```

This command lets you modify one or more rules.

The `--add` option allows you to add a release to each of the rules if 
it does not already exist.

The `--remove` option allows you to remove a release from each of the
rules, if it exists.

The rule changes are added to Balrog as "Scheduled Changes" as this is
how sign-offs are handled on live channels. The changes are scheduled
for 5 seconds in the future so they should take effect immediately after
any required sign-offs are received.
