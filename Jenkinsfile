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
                   echo 'Tests will go here'
               }
           }
       }
   }
