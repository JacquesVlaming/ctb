# Capture the Bug - Local Setup Instruction

**DEPRECATED** - The preferred way to use CTB is through a machine image that comes pre-built with the ctb tool and its dependencies. The local setup instructions on this page were lasted tested in March 2021.


## Infrastructure

CTB resources are on the `elastic-sa` project on GCP. If you're having trouble deploying a cluster on GKE, verify if your account has permission to use these resources.


## Prepare your local instructor environment

The following instructions were tested only on **MacOS**.

**Install Python**

Install [Python](https://www.python.org/downloads/) and [pip](https://pip.pypa.io/en/stable/installing/) if they are not already installed in your environment.

**Install tooling**

```sh
brew install docker
brew install docker-machine
brew cask install virtualbox
brew install kubectl
brew install skaffold
```

**Install and configure gcloud**

```sh
curl https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-311.0.0-darwin-x86_64.tar.gz | tar -xz
./google-cloud-sdk/install.sh --quiet
export PATH=$(pwd)/google-cloud-sdk/bin:$PATH
gcloud init
```

**Authenticate and then pick the `elastic-sa` project**

```sh
gcloud services enable container.googleapis.com
gcloud components install beta
gcloud components install docker-credential-gcr
gcloud auth configure-docker -q
```

**Run Docker**

Download and run [Docker Desktop for Mac](https://hub.docker.com/editions/community/docker-ce-desktop-mac).

The docker daemon must be running to build the images for the Hipster Shop services and monitoring agents.


## Clone this repo

```sh
git clone https://github.com/elastic/ctb.git
cd ctb
```


## Install ctb

Run this comand at the root-level directory of the repo.

```sh
sudo python setup.py develop
```

Ensure that ./ctb is executable:

```sh
chmod a+x ctb
```
