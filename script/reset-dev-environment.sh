#!/bin/bash

# Step 1: Clean Docker Containers and Images
echo "Stopping and removing all Docker containers..."
docker stop $(docker ps -aq) && docker rm $(docker ps -aq)

echo "Removing unused Docker images, volumes, and networks..."
docker system prune -af --volumes

# Step 2: Reset Local Git Repository
echo "Resetting local Git repository..."
git reset --hard HEAD
git clean -fd
git pull origin main

# Step 3: Reinstall Dependencies
echo "Reinstalling Python dependencies..."
pip install -r script/requirements.txt

echo "Installing Ansible collections..."
ansible-galaxy install -r ansible/requirements.yml

echo "Updating Helm dependencies..."
helm dependency update helm/*

# Step 4: Reinitialize the Environment
echo "Reinitializing NOAH CLI..."
./noah.sh init

echo "Reconfiguring the pipeline..."
./noah.sh setup-pipeline

# Step 5: Validate the Environment
echo "Running CI test job locally..."
act -j test -P ubuntu-latest=catthehacker/ubuntu:act-latest

echo "Validating Ansible playbooks syntax..."
ansible-playbook --syntax-check ansible/playbooks/*.yml

echo "Linting Helm charts..."
for chart in helm/*; do
  helm lint "$chart"
done

echo "Development environment reset complete!"
