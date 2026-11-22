pipeline {
    agent any

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
    }

    parameters {
        booleanParam(name: 'PUSH_IMAGE', defaultValue: false, description: 'Push built image to Docker Hub')
        booleanParam(name: 'DEPLOY', defaultValue: false, description: 'Deploy demo container environment (main branch only)')
    }

    environment {
        IMAGE_NAME = 'student-api'
        DOCKERHUB_REPO = 'student-api'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    def shortCommit = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
                    env.GIT_COMMIT_SHORT = shortCommit
                    echo "Building ${IMAGE_NAME} image with tags: ${BUILD_NUMBER}, ${shortCommit}, and latest"
                    sh """
                        docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} -t ${IMAGE_NAME}:${shortCommit} -t ${IMAGE_NAME}:latest .
                    """
                }
            }
        }

        stage('Validate') {
            steps {
                echo 'Validating Docker Compose configuration and Python code syntax...'
                sh '''
                    # Validate Compose configuration syntax
                    MYSQL_ROOT_PASSWORD=ci_dummy_root_pw \
                    DB_NAME=student_db \
                    DB_USER=student_app \
                    DB_PASSWORD=ci_dummy_app_pw \
                    SECRET_KEY=ci_dummy_secret_key \
                    docker compose config -q

                    # Validate Python syntax inside built container without bind mounts
                    docker run --rm --entrypoint sh ${IMAGE_NAME}:${BUILD_NUMBER} -c '
                        set -e
                        COUNT=$(find /app -name "*.py" | wc -l)
                        echo "Found ${COUNT} Python files to validate."
                        python -m compileall -q /app
                        echo "All ${COUNT} Python files passed syntax compilation."
                    '
                '''
            }
        }

        stage('Test') {
            environment {
                CI_PROJECT = "student-ci-${BUILD_NUMBER}"
            }
            steps {
                echo "Running integration test suite in isolated CI environment: ${CI_PROJECT}..."
                sh '''
                    # Temporarily disable shell tracing so generated secrets are not printed
                    set +x
                    echo "Generating isolated CI credentials..."
                    CI_ROOT_PW=$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')
                    CI_APP_PW=$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')
                    CI_SECRET=$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')

                    cat <<EOF > .env.ci
MYSQL_ROOT_PASSWORD=${CI_ROOT_PW}
DB_HOST=db
DB_PORT=3306
DB_NAME=student_db
TEST_DB_NAME=student_test_db
DB_USER=student_app
DB_PASSWORD=${CI_APP_PW}
SECRET_KEY=${CI_SECRET}
FLASK_DEBUG=0
EOF
                    # Re-enable shell tracing
                    set -x

                    # Override web ports for CI to guarantee no host port conflicts
                    cat <<EOF > docker-compose.ci.yml
services:
  web:
    ports: !reset []
EOF

                    docker compose -p ${CI_PROJECT} -f docker-compose.yml -f docker-compose.ci.yml --env-file .env.ci up -d --build

                    # Wait for database container to report healthy
                    echo "Waiting for CI database to become healthy..."
                    retries=30
                    while [ $retries -gt 0 ]; do
                        if [ "$(docker inspect --format='{{.State.Health.Status}}' ${CI_PROJECT}-db-1 2>/dev/null)" = "healthy" ]; then
                            echo "CI database is healthy."
                            break
                        fi
                        retries=$((retries - 1))
                        sleep 2
                    done

                    # Run tests inside web container with JUnit XML reporting
                    docker compose -p ${CI_PROJECT} -f docker-compose.yml -f docker-compose.ci.yml --env-file .env.ci exec -T web pytest -v --junitxml=junit-results.xml

                    # Copy results out of container for Jenkins publishing
                    docker cp ${CI_PROJECT}-web-1:/app/junit-results.xml ./junit-results.xml || true

                    # Clean up CI environment and remove temporary files
                    docker compose -p ${CI_PROJECT} -f docker-compose.yml -f docker-compose.ci.yml --env-file .env.ci down -v
                    rm -f .env.ci docker-compose.ci.yml
                '''
                junit testResults: 'junit-results.xml', allowEmptyResults: true
            }
        }

        stage('Push to Docker Hub') {
            when {
                expression { return params.PUSH_IMAGE == true }
            }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh '''
                        echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin
                        docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${DOCKER_USER}/${DOCKERHUB_REPO}:${BUILD_NUMBER}
                        docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${DOCKER_USER}/${DOCKERHUB_REPO}:${GIT_COMMIT_SHORT}
                        docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${DOCKER_USER}/${DOCKERHUB_REPO}:latest
                        docker push ${DOCKER_USER}/${DOCKERHUB_REPO}:${BUILD_NUMBER}
                        docker push ${DOCKER_USER}/${DOCKERHUB_REPO}:${GIT_COMMIT_SHORT}
                        docker push ${DOCKER_USER}/${DOCKERHUB_REPO}:latest
                    '''
                }
            }
        }

        stage('Deploy (demo)') {
            when {
                expression { params.DEPLOY && (env.GIT_BRANCH == 'origin/main' || env.GIT_BRANCH == 'main') }
            }
            steps {
                withCredentials([file(credentialsId: 'student-demo-env', variable: 'DEMO_ENV_FILE')]) {
                    echo 'Deploying demo application container stack...'
                    sh '''
                        docker compose -p student-demo --env-file "${DEMO_ENV_FILE}" up -d --build

                        # Verify deployment health
                        echo "Verifying student-demo container health..."
                        retries=30
                        healthy=false
                        while [ $retries -gt 0 ]; do
                            status=$(docker inspect --format='{{.State.Health.Status}}' student-demo-web-1 2>/dev/null || true)
                            if [ "$status" = "healthy" ]; then
                                echo "Demo container student-demo-web-1 is healthy."
                                healthy=true
                                break
                            fi
                            if docker exec student-demo-web-1 python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:5000/health').getcode() == 200 else 1)" >/dev/null 2>&1; then
                                echo "Demo container student-demo-web-1 responded 200 on /health directly."
                                healthy=true
                                break
                            fi
                            retries=$((retries - 1))
                            sleep 2
                        done

                        if [ "$healthy" != "true" ]; then
                            echo "Deployment healthcheck failed: container student-demo-web-1 status is '${status}'"
                            docker compose -p student-demo --env-file "${DEMO_ENV_FILE}" logs web --tail 50
                            exit 1
                        fi

                        # Verify /health response payload directly from the container
                        docker exec student-demo-web-1 python -c "import urllib.request; resp = urllib.request.urlopen('http://localhost:5000/health'); print('Health check payload:', resp.read().decode())"
                    '''
                }
            }
        }
    }

    post {
        always {
            sh '''
                docker compose -p student-ci-${BUILD_NUMBER} down -v 2>/dev/null || true
                docker image prune -f 2>/dev/null || true
                rm -f .env.ci docker-compose.ci.yml
            '''
        }
        success {
            echo "Pipeline build #${BUILD_NUMBER} completed successfully!"
        }
        failure {
            echo "Pipeline build #${BUILD_NUMBER} encountered an error and failed."
        }
    }
}
