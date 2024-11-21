#!/bin/bash

IMAGE_NAME="hackathon"
CONTAINER_NAME="hackathon_container"
PORT=8501

echo "Building the Docker image..."
docker build -t $IMAGE_NAME .

if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
    echo "Stopping and removing existing container..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi

echo "Running the Docker container..."
docker run --name $CONTAINER_NAME -p $PORT:8501 $IMAGE_NAME

echo "Streamlit app is running at http://localhost:$PORT"
