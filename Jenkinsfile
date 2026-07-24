pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Build Docker Image') {
            steps {
                sh 'docker build -t student-api .'
            }
        }
        stage('Test') {
            steps {
                sh 'pip install -r requirements.txt'
                sh 'pytest tests/ -v'
            }
        }
        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh 'echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin'
                    sh 'docker tag student-api $DOCKER_USER/student-api:latest'
                    sh 'docker push $DOCKER_USER/student-api:latest'
                }
            }
        }
    }
}
