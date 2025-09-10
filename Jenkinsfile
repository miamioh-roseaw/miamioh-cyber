pipeline {
    agent any
    
    environment {
        // Docker and Kubernetes configuration
        DOCKER_REGISTRY = 'your-registry.com'  // Change this to your registry
        IMAGE_NAME = 'gns3-cyberrange'
        IMAGE_TAG = "${BUILD_NUMBER}"
        KUBECONFIG_CREDENTIAL_ID = 'kubeconfig'  // Jenkins credential ID for kubeconfig
        DOCKER_CREDENTIAL_ID = 'docker-registry-creds'  // Jenkins credential ID for Docker registry
        
        // Application configuration
        APP_NAMESPACE = 'cyberrange'
        APP_NAME = 'gns3-cyberrange'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_COMMIT_SHORT = sh(
                        script: "git rev-parse --short HEAD",
                        returnStdout: true
                    ).trim()
                }
            }
        }
        
        stage('Test') {
            steps {
                sh '''
                    python -m venv test-env
                    . test-env/bin/activate
                    pip install -r requirements.txt
                    pip install pytest pytest-cov flake8
                    
                    # Run linting
                    flake8 app.py --max-line-length=100 --ignore=E501,W503
                    
                    # Run tests (if you have any)
                    # pytest tests/ --cov=app --cov-report=xml
                '''
            }
            post {
                always {
                    sh 'rm -rf test-env'
                }
            }
        }
        
        stage('Build Docker Image') {
            steps {
                script {
                    def fullImageName = "${DOCKER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
                    env.FULL_IMAGE_NAME = fullImageName
                    
                    // Build the Docker image
                    sh """
                        docker build -t ${fullImageName} .
                        docker tag ${fullImageName} ${DOCKER_REGISTRY}/${IMAGE_NAME}:latest
                    """
                }
            }
        }
        
        stage('Security Scan') {
            steps {
                script {
                    // Example using Trivy for container scanning
                    sh """
                        # Install trivy if not available
                        if ! command -v trivy &> /dev/null; then
                            wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
                            echo deb https://aquasecurity.github.io/trivy-repo/deb \$(lsb_release -sc) main | sudo tee -a /etc/apt/sources.list.d/trivy.list
                            sudo apt-get update
                            sudo apt-get install trivy
                        fi
                        
                        # Scan the image
                        trivy image --exit-code 0 --severity HIGH,CRITICAL ${FULL_IMAGE_NAME}
                    """
                }
            }
        }
        
        stage('Push to Registry') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: env.DOCKER_CREDENTIAL_ID, 
                                                   usernameVariable: 'DOCKER_USER', 
                                                   passwordVariable: 'DOCKER_PASS')]) {
                        sh """
                            echo \$DOCKER_PASS | docker login ${DOCKER_REGISTRY} -u \$DOCKER_USER --password-stdin
                            docker push ${FULL_IMAGE_NAME}
                            docker push ${DOCKER_REGISTRY}/${IMAGE_NAME}:latest
                        """
                    }
                }
            }
        }
        
        stage('Deploy to Development') {
            when {
                branch 'develop'
            }
            steps {
                script {
                    deployToEnvironment('development')
                }
            }
        }
        
        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            steps {
                script {
                    // Add approval step for production
                    input message: 'Deploy to Production?', ok: 'Deploy'
                    deployToEnvironment('production')
                }
            }
        }
    }
    
    post {
        always {
            // Clean up Docker images
            sh """
                docker rmi ${FULL_IMAGE_NAME} || true
                docker rmi ${DOCKER_REGISTRY}/${IMAGE_NAME}:latest || true
                docker system prune -f
            """
        }
        
        success {
            echo 'Pipeline completed successfully!'
        }
        
        failure {
            echo 'Pipeline failed!'
            // Add notification logic here (Slack, email, etc.)
        }
    }
}

def deployToEnvironment(environment) {
    withCredentials([file(credentialsId: env.KUBECONFIG_CREDENTIAL_ID, variable: 'KUBECONFIG')]) {
        sh """
            # Update the image tag in the deployment manifest
            sed -i 's|IMAGE_TAG_PLACEHOLDER|${IMAGE_TAG}|g' k8s/overlays/${environment}/kustomization.yaml
            sed -i 's|DOCKER_REGISTRY_PLACEHOLDER|${DOCKER_REGISTRY}|g' k8s/overlays/${environment}/kustomization.yaml
            
            # Apply Kubernetes manifests
            kubectl apply -k k8s/overlays/${environment}/
            
            # Wait for rollout to complete
            kubectl rollout status deployment/${APP_NAME} -n ${APP_NAMESPACE}-${environment} --timeout=300s
            
            # Verify deployment
            kubectl get pods -n ${APP_NAMESPACE}-${environment} -l app=${APP_NAME}
        """
    }
}
