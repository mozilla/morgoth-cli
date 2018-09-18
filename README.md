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

**Note:** You can leave out the `--editable` flag however you will
then need to reinstall any time you update the repo.

### Configuration

To configure this tool simply run the following command:

```
$ morgoth init
```

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

