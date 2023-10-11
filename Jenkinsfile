@Library('ftw-shared-libs')_
pipeline {
    agent {
        node {
            label '!django'
        }
    }
    options {
        ansiColor('xterm')
    }
    environment {
        CI    = 'true'
        PATH = '/var/lib/jenkins/bin:/usr/local/rbenv/shims:/usr/local/bin:/var/lib/jenkins/bin:/usr/local/rbenv/shims:/usr/local/rbenv/bin:/usr/local/bin:/usr/bin:/opt/puppetlabs/bin'
    }
    stages {
        stage('Run Tests') {
            stage('test-plone-4.3.x') {
                agent {
                    node {
                        label '!django'
                        customWorkspace "workspace/${JOB_NAME}/test-plone-4.3.x/${BUILD_NUMBER}"
                    }
                }
                steps {
                    allocatePorts()
                    withChecks(name: 'test-plone-4.3.x') {
                        sh "${JENKINS_BUILD} test-plone-4.3.x.cfg"
                        publishChecks()
                    }
                }
            }
        }
    }
    post {
        failure {
            script {
                slackNotification()
            }
        }
    }
}