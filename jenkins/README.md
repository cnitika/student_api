# Custom Jenkins Controller with Docker CLI & Plugins

> [!NOTE]
> **Status:** **NOT VERIFIED** (Created for manual activation after Phase 4 approval. Per explicit phase instructions, the Jenkins server container was NOT built or started in this phase).

This directory contains the custom Dockerfile and instructions for running a self-contained Jenkins controller capable of orchestrating Docker builds and tests via the host Docker daemon.

---

## 1. Build the Custom Jenkins Image

From the repository root directory (`student_api/`):

```bash
docker build -t custom-jenkins:lts ./jenkins
```

*(On Windows PowerShell, use the same command).*

---

## 2. Run the Jenkins Controller Container

Run Jenkins mounting the host's Docker socket, creating a persistent volume `jenkins_home`, and mapping web UI port `8080` and agent port `50000`:

```bash
docker run -d \
  --name jenkins \
  --restart unless-stopped \
  -p 8080:8080 \
  -p 50000:50000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v jenkins_home:/var/lib/jenkins \
  custom-jenkins:lts
```

### Docker Socket Permissions (Linux / WSL2 Host)
If the `jenkins` user inside the container cannot communicate with `/var/run/docker.sock` due to permissions, execute:

```bash
docker exec -u root jenkins chmod 666 /var/run/docker.sock
```

---

## 3. Retrieve Initial Admin Password

Unlock Jenkins on first launch at `http://localhost:8080` using:

```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

---

## 4. Manual Jenkins UI Configuration Checklist

### A. Credentials Setup (`Manage Jenkins` -> `Credentials` -> `System` -> `Global credentials`)
1. **Docker Hub Credentials (Username and Password):**
   - **Kind:** Username with password
   - **ID:** `dockerhub-creds`
   - **Username:** Your Docker Hub username
   - **Password:** Your Docker Hub Personal Access Token (PAT)
2. **Demo Environment Secret File (Secret file):**
   - **Kind:** Secret file
   - **ID:** `student-demo-env`
   - **File:** Upload a `.env.production` file containing production database credentials and `SECRET_KEY`.

### B. Create Pipeline Job
1. Click **New Item** -> Name: `student-api-pipeline` -> Select **Pipeline** -> Click **OK**.
2. Under **Pipeline Definition**, select **Pipeline script from SCM**.
3. **SCM:** `Git`
4. **Repository URL:** `https://github.com/rijooanhasan-ctrl/student_api.git`
5. **Branch Specifier:** `*/feature/marks-management` (or `*/main`)
6. **Script Path:** `Jenkinsfile`
7. Click **Save**.

### C. Trigger Build
Click **Build with Parameters**:
- `PUSH_IMAGE`: Check `true` if you wish to push to Docker Hub; leave unchecked for local build & test only.
- `DEPLOY`: Check `true` to test the demo deployment stage (requires branch `main`).
