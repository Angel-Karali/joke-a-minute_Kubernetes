# Joke-a-Minute – Kubernetes Deployment

This repository contains a Kubernetes-based deployment of the *Joke-a-Minute* application.
The project is a migration of a previously Docker Compose–based application to Kubernetes.
The main goal is to demonstrate **container orchestration, high availability, persistence,
secure ingress, CI/CD, and Kubernetes deployment strategies**.

The application was first made to work correctly and reliably, and only afterwards documented,
to ensure that all described features are actually implemented and tested.

---

## Application Architecture

The application stack consists of the following components:

### Flask Application
- Python Flask application served using **Gunicorn**
- Deployed as a Kubernetes **Deployment**
- Runs with **3 replicas** to provide high availability
- Exposes a `/health` endpoint used for:
  - readiness probes
  - liveness probes
- Stateless application logic

### MySQL
- Deployed as a Kubernetes **StatefulSet**
- Uses a **PersistentVolumeClaim** for data storage
- Stores application data (jokes)
- Database credentials are provided via Kubernetes **Secrets**

### Redis
- Used as a cache layer
- Deployed as a Kubernetes **Deployment**
- Uses a **PersistentVolumeClaim** to persist cached data

### Ingress and Networking
- **NGINX Ingress Controller** is used
- Application is exposed via a public hostname
- HTTPS is enabled using **cert-manager**

### TLS Certificates
- Managed automatically using **cert-manager**
- **Let’s Encrypt staging certificates** are used during development
- Certificates are automatically issued and renewed

### CI/CD
- Implemented using **GitHub Actions**
- Automatically builds and publishes Docker images to **GitHub Container Registry (GHCR)**
- Images are tagged with immutable tags (commit SHA / version)
- The `:latest` tag is intentionally not used in Kubernetes manifests

---

## Prerequisites

- Linux virtual machine (tested on Ubuntu)
- Docker
- kubectl
- MicroK8s (or another Kubernetes cluster)
- GitHub account (for Container Registry and CI/CD)

---

## Cluster Setup (One-Time)

Install MicroK8s and configure kubectl access:

```bash
sudo snap install microk8s --classic
sudo usermod -aG microk8s $USER
mkdir -p ~/.kube
sudo microk8s config > ~/.kube/config
```

Enable required MicroK8s addons:

```bash
sudo microk8s enable dns
sudo microk8s enable ingress
sudo microk8s enable hostpath-storage
```

These addons provide:
- internal DNS resolution
- ingress controller
- default storage class for PersistentVolumes


## How to Run the Project

### 1. Create Kubernetes Secrets

Sensitive data is not committed to Git.
Instead, a template file is provided.

```bash
cp k8s/mysql/secret.example.yaml k8s/mysql/secret.yaml
kubectl apply -f k8s/mysql/secret.yaml
```

This Secret contains:
- MySQL root password
- database name
- application database user and password

---

### 2. Deploy the Application Stack

Deploy all Kubernetes resources at once:

```bash
kubectl apply -f k8s/
```

This deploys:
- MySQL StatefulSet and Service
- Redis Deployment and Service
- Flask application Deployment and Service
- Ingress configuration

---

### 3. Initialize the Database

Database initialization is handled using a **Kubernetes Job**:

```bash
kubectl apply -f k8s/app/init-db-job.yaml
```

The Job:
- connects to the MySQL service
- creates required tables if they do not exist
- inserts initial data

This replaces the manual `docker exec` database initialization used in the Docker Compose setup.

---

### 4. Access the Application

The application is available at:

```text
https://<your-domain>
```

During development, Let’s Encrypt **staging certificates** are used.
Browsers may show a security warning, which is expected.

---

# Overview

###  MySQL Deployment (StatefulSet, Service, Persistent Storage)

In the original Docker Compose setup, MySQL was started as a single container with a mounted volume.
When migrating to Kubernetes, this was reimplemented using native Kubernetes primitives to correctly handle state, persistence, and networking.

All MySQL-related manifests are located in:

 ```bash
k8s/mysql/
```
---

#### PersistentVolumeClaim (pvc.yaml)

MySQL stores persistent data and therefore must not lose data when pods are restarted or rescheduled.
For this reason, a PersistentVolumeClaim (PVC) is used.

The PVC:
- requests persistent storage from the cluster
- is independent of the MySQL Pod lifecycle
- ensures database data survives pod restarts and updates

This replaces the Docker volume used in the Docker Compose version.

---
**Service (service.yaml)**

A Kubernetes Service is created to provide a stable network identity for MySQL.

**The Service:**
- exposes MySQL internally on port 3306
- allows other components (Flask app, init-db Job) to connect using the hostname mysql
- decouples clients from the actual Pod IP address

Using a Service ensures reliable internal communication even if the MySQL Pod is recreated.

--- 

**StatefulSet (statefulset.yaml)**

MySQL is deployed using a StatefulSet, not a Deployment.

A StatefulSet is used because:
- SQL is a stateful application
- it requires stable pod identity
- it must be bound to a persistent volume

The StatefulSet:
- ensures the MySQL Pod keeps the same identity across restarts
- mounts the PersistentVolumeClaim into the container
- receives database credentials via Kubernetes Secrets

Using a StatefulSet is the recommended Kubernetes approach for databases and other stateful workloads.

Configuration via Kubernetes Secrets
Database credentials (user, password, database name) are not hardcoded in the manifests.

Instead:
- credentials are stored in a Kubernetes Secret
- the StatefulSet loads them as environment variables
- the actual secret values are excluded from version control

A secret.example.yaml file documents the required keys, while the real secret is created locally.

### Redis Deployment

The Redis configuration is defined in the k8s/redis/ directory. A pvc.yaml file is used to create a PersistentVolumeClaim, which provides storage independent of the pod lifecycle. This ensures that Redis data is not lost if the Redis pod is restarted or recreated.

Redis itself is deployed using a Deployment defined in deployment.yaml. A Deployment is sufficient because Redis does not require stable pod identity. The PersistentVolumeClaim is mounted into the container to store Redis data on disk.

A Service defined in service.yaml provides stable internal access to Redis. The Flask application connects to Redis using the service name redis, allowing the Redis pod to be replaced without affecting connectivity.

This setup demonstrates how persistent storage in Kubernetes replaces Docker volumes and allows Redis data to survive pod restarts.


## Ingress (Public Access + HTTPS)

To expose the Flask application publicly, we used NGINX Ingress. Instead of opening a NodePort or LoadBalancer directly on the app Service, the Ingress acts as a single entry point that routes external HTTP/HTTPS traffic to the correct Kubernetes Service.

**k8s/ingress/ingress.yaml**


#### Host routing
```bash
rules:
  - host: devops-sk-10.lrk.si
```
This tells the Ingress to only handle requests coming to this hostname. This is required for proper TLS certificates as well, because Let’s Encrypt issues certificates for a specific domain.


#### Path routing to the app Service

```bash
paths:
  - path: /
    pathType: Prefix
    backend:
      service:
        name: app
        port:
          number: 80
```
This means: all requests to / (and anything under it because Prefix) are forwarded to the Kubernetes Service named app on port 80. The Service then load-balances traffic across the app pods.

#### ingressClassName
```bash
ingressClassName: public
```
This binds the Ingress to the NGINX ingress controller class we use in MicroK8s. Without the correct ingress class, the controller would ignore the Ingress and it would never become active.

#### Rewrite annotation (optional but used)
```bash
nginx.ingress.kubernetes.io/rewrite-target: /
```
This is an NGINX ingress annotation that rewrites the incoming path before forwarding it to the backend. In our case the application is served from /, so this keeps routing consistent. (If the app routes directly from / already, this annotation does not harm but can be useful when routing multiple apps under different paths.)


## TLS with cert-manager (Let’s Encrypt)

To enable HTTPS and automatic certificate renewal we used cert-manager, which watches the Ingress and automatically creates/renews certificates.

In the Ingress we added:

```bash
cert-manager issuer annotation
cert-manager.io/cluster-issuer: letsencrypt-staging
```

This tells cert-manager which issuer to use when generating a certificate for the hostname. We used Let’s Encrypt staging during development to avoid production rate limits.

TLS section
```bash
tls:
  - hosts:
      - devops-sk-10.lrk.si
    secretName: joke-app-tls
```

This enables HTTPS for the host and defines where the TLS certificate is stored. cert-manager creates and maintains the secret named joke-app-tls. The Ingress controller then uses that secret to terminate HTTPS.

**ClusterIssuer (staging)**

The Let’s Encrypt staging issuer is defined in:

```bash
k8s/ingress/cluster-issuer-staging.yaml
```

Key lines:

```bash
server: https://acme-staging-v02.api.letsencrypt.org/directory
```
This selects Let’s Encrypt’s staging API endpoint. Staging certificates are not trusted by browsers by default, but they work for testing and do not hit production limits.

```bash
solvers:
  - http01:
      ingress:
        class: public
```
This configures HTTP-01 validation, meaning Let’s Encrypt verifies domain ownership by sending a request to your domain over HTTP. The solver uses the public ingress class, so the challenge is served through the same ingress controller.


Switching from Staging to Production Certificates

 For the final deployment, switching to trusted production certificates only requires changing the Ingress annotation to reference the production issuer (letsencrypt-prod) and reapplying the manifest. cert-manager then automatically issues a trusted certificate and stores it in the same Kubernetes Secret, without requiring any changes to the application or Services.


## Secrets Management

In the original Docker Compose setup, sensitive configuration such as database passwords was provided through a local .env file. This file was excluded from version control using .gitignore. When migrating the project to Kubernetes, this approach was replaced with Kubernetes Secrets, which are the native and recommended way to manage sensitive data in a cluster.

All secret-related configuration is located in:

```BASH
k8s/mysql/
```

#### Secret manifest template

The file **secret.example.yaml** defines the structure of the required secret, but does not contain real credentials. This file is safe to commit to Git and serves as documentation for which values must be provided.

Example lines from the file:

```BASH
apiVersion: v1
kind: Secret
metadata:
  name: mysql-secret
type: Opaque
stringData:
  MYSQL_ROOT_PASSWORD: "CHANGE_ME_ROOT"
  MYSQL_DATABASE: "jokes"
  MYSQL_USER: "jokeuser"
  MYSQL_PASSWORD: "CHANGE_ME_USER"
```

The **stringData** section allows secret values to be written in plain text, which Kubernetes automatically base64-encodes when storing the Secret internally. The placeholder values clearly indicate which fields must be replaced locally.

### Local secret creation

The actual secret used by the cluster is created locally by copying the template file:

```bash
cp k8s/mysql/secret.example.yaml k8s/mysql/secret.yaml
kubectl apply -f k8s/mysql/secret.yaml
```

The real **secret.yaml** file is excluded from version control and contains the actual credentials. This ensures that sensitive information is never pushed to the repository.


### Using the Secret in workloads

The Secret is consumed by the MySQL StatefulSet, the Flask application Deployment, and the database initialization Job via explicitly defined environment variables. Instead of injecting all secret values automatically, each required variable is mapped individually using secretKeyRef. This makes the configuration clearer and avoids unintentionally exposing unused secret values.

For example, in the MySQL StatefulSet manifest:

```bash
env:
  - name: MYSQL_DATABASE
    valueFrom:
      secretKeyRef:
        name: mysql-secret
        key: MYSQL_DATABASE
  - name: MYSQL_USER
    valueFrom:
      secretKeyRef:
        name: mysql-secret
        key: MYSQL_USER
  - name: MYSQL_PASSWORD
    valueFrom:
      secretKeyRef:
        name: mysql-secret
        key: MYSQL_PASSWORD
```

This approach ensures that only the necessary credentials are injected into each container and that all components use a consistent and explicitly defined set of database credentials.

## CI/CD Pipeline

To automate building and publishing container images, a GitHub Actions workflow was created. The workflow is triggered on pushes to the main branch and on version tags. It builds the application image using the provided Dockerfile and publishes it to GitHub Container Registry (GHCR).

The workflow ensures that each image is tagged with a unique and immutable identifier (such as a commit SHA or version), which allows Kubernetes deployments to reference fixed image versions. This avoids using the ```:latest``` tag and makes deployments reproducible.

On each push to the main branch:
1. The repository is checked out
2. The Docker image is built using a multi-stage Dockerfile
3. The image is tagged with immutable tags
4. The image is pushed to GitHub Container Registry (GHCR)

Kubernetes manifests always reference a **fixed image tag**, ensuring reproducible deployments.


## Readiness & Liveness Probes (Why these values)

The Flask application exposes a `/health` endpoint which checks the application status and connectivity to its dependencies (MySQL and Redis). We use this endpoint for both readiness and liveness probes, but with different timings, because they serve different purposes.

### Readiness Probe (traffic control)

```bash
readinessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 2
  failureThreshold: 6
```
The readiness probe uses the `/health` endpoint to determine when the application is ready to receive traffic. A short initial delay allows the Flask app to start quickly, while frequent checks ensure that pods are added to the Service as soon as they become healthy. If the application cannot reach its dependencies (MySQL or Redis), the pod is marked as NotReady and traffic is temporarily stopped, preventing failed requests during deployments.


### Liveness Probe (automatic recovery)

```bash
livenessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 20
  periodSeconds: 10
  timeoutSeconds: 2
  failureThreshold: 6
```
The liveness probe also uses the `/health` endpoint but starts later than the readiness probe to avoid restarting the container during normal startup. The longer delay and failure threshold allow short transient issues to recover naturally, while still ensuring that the pod is restarted if the application becomes permanently unhealthy.

### Why these values were chosen?

These probe settings were chosen to balance fast availability and stability. Pods become ready quickly when healthy, but are not restarted or exposed to traffic during short dependency issues. This behavior is especially important during rolling updates and blue/green deployments, where uninterrupted service availability is required.

---

## Rolling Update Strategy


Rolling Update with Zero Downtime

To demonstrate a rolling update with zero downtime, the Flask application Deployment was configured with a controlled rolling update strategy and multiple replicas. The goal was to update the application version while ensuring that the service remained continuously available.

The application Deployment is configured with three replicas and the following rolling update strategy:

```bash
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 0
    maxSurge: 1
```

Setting ```maxUnavailable: 0``` ensures that no running pod is taken down before a new pod is ready. This guarantees that the application never runs with fewer replicas than declared. Setting ```maxSurge: 1``` allows Kubernetes to temporarily create one additional pod during the update, which makes it possible to replace pods one by one without downtime.

To demonstrate this behavior, a new version of the application image was built and pushed via the CI/CD pipeline. The Kubernetes Deployment was then updated to reference the new image tag.

While the update was in progress, continuous HTTP requests were sent to the application endpoint using a looped curl command. Throughout the entire update process, all requests returned 200 OK, confirming that the application remained available at all times.

At the same time, pod status was monitored using ```kubectl get pods -w```. The output clearly shows that:

- a new pod is created and becomes ready
- only after the new pod is ready, an old pod is terminated
- at most one pod is updated at a time
- the number of ready pods never drops below three

Screenshots taken during the rollout show the temporary presence of an extra pod (due to ```maxSurge: 1```) and the gradual replacement of old pods with new ones. A visible UI change (background color) was also used to confirm that the new application version was successfully deployed.

This demonstrates a correct rolling update with zero downtime, where Kubernetes safely replaces application instances without interrupting client traffic.


![alt text](images/new%20pods.png)
A new pod is created while the existing three pods are still running, demonstrating the use of maxSurge: 1 during the rolling update.

![alt text](images/Pod%20replacement%20in%20progress.png)
Once the new pod becomes ready, an old pod enters the terminating state, showing that pods are replaced one at a time.

![alt text](images/Rolling%20update%20strategy%20configuration.png)
This screenshot confirms the rolling update configuration with maxUnavailable: 0 and maxSurge: 1, ensuring zero downtime during the update.

![alt text](images/Rollout%20completion.png)
The rollout finishes successfully, and all application pods are running the new version, confirming a completed rolling update without service interruption.

## Blue/Green Deployment

To demonstrate a Blue/Green deployment strategy, two separate versions of the Flask application were deployed simultaneously in the cluster. The goal of this approach is to enable instant traffic switching between application versions without restarting pods and without any downtime.

Two independent Kubernetes Deployments were created:

- `joke-app-blue`

- `joke-app-green`

Both deployments run the same application but reference different container image versions. The blue deployment represents the currently stable version of the application, while the green deployment represents a new version with a visible UI change (background color), making it easy to verify which version is receiving traffic.

Each Deployment runs with three replicas and uses the same readiness and liveness probes. This ensures that both versions are fully healthy and capable of serving traffic before any switching occurs.

### Traffic Control via Service Selector

Instead of exposing each Deployment separately, a single Kubernetes Service is used to control traffic flow. The Service selects pods based on labels, specifically the version label.

Initially, the Service selector is configured to route traffic to the blue deployment:

```bash
selector:
  app: joke-app
  version: blue
```

![alt text](images/blue%20and%20both%20deployed.png)


![alt text](images/service%20points%20BLUE.png)

At this point:

- both blue and green pods are running
- only the blue pods receive traffic
- the green pods remain idle but ready


### Switching Traffic from Blue to Green

To perform the Blue/Green switch, the Service selector is updated to point to the green version:

```bash
selector:
  app: joke-app
  version: green
```

After applying this change, traffic is immediately redirected to the green pods. No pods are restarted and no rolling update occurs at this stage. The switch happens instantly at the Service level.

To verify zero downtime, continuous HTTP requests were sent to the application endpoint while the Service selector was changed. All requests returned 200 OK, confirming uninterrupted availability. The visible UI change further confirmed that traffic was now being served by the green version.

<video src="images/Screen Recording 2026-01-17 210307.mp4" width="1080" height="500" controls></video>


## Container Image Design

The application image uses a **multi-stage Docker build**:

- Builder stage:
  - installs Python dependencies
- Runtime stage:
  - based on `python:3.11-slim`
  - contains only runtime dependencies

This significantly reduces image size while maintaining compatibility with required libraries.


## Summary

This project demonstrates:

- Kubernetes-based application orchestration
- Persistent storage using PVCs
- Secure ingress with TLS
- CI/CD-driven container builds
- Zero-downtime rolling updates
- Blue/Green deployment strategy

All features were implemented and tested in a real Kubernetes environment.
