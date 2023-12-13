from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
import io
from typing import List, Optional, Tuple
from dataclasses import asdict
import hydra
from loguru import logger
from omegaconf import DictConfig, OmegaConf
import numpy as np
import os
import pyrootutils
from hydra import compose, initialize
from src.core.core import init_pipeline
import boto3

# find absolute root path (searches for directory containing any of the files on the list)
base_path = pyrootutils.find_root(search_from=__file__, indicator=[".git", "setup.cfg"])
REGION = os.environ.get("REGION", "us-west-2")

app = FastAPI()

def setup_pipeline():
    with initialize(version_base="1.1", config_path="../../configs"):
        cfg = compose(config_name="pipeline-tibhannover.yaml", overrides=[])
        pipeline = init_pipeline(cfg)
        return pipeline

class Predictor():
    def __init__(self):
        self.pipeline = setup_pipeline()

    def predict(self, img):
        output = {
            "image": Image.open(img).convert("RGB")
        }

        for module in self.pipeline:
            if type(output) != dict:
                output = module(output)
            else:
                output = module(**output)
        return output

predictor = Predictor()

print("Predictor initialized")

def predict_coords(file):
    try:
        prediction = predictor.predict(file)
        return prediction.get('coordinates')
    except Exception as e:
        print('error', e)
        return JSONResponse(content={"error": str(e)}, status_code=500)

def get_location_info(latitude, longitude, location_index_name="AskMeWherePlaceIndex"):
    # Initialize Amazon Location Service client
    client = boto3.client('location', region_name=REGION)

    # Construct the position parameter
    position = [longitude, latitude]

    try:
        # Query Amazon Location Service for location information
        response = client.search_place_index_for_position(
            IndexName=location_index_name,  # Replace with the name of your place index
            Position=position
        )

        # Extract location information from the response
        place = [response['Results'][0]]
        return place

    except Exception as e:
        print(f"Error: {e}")
        return [] 

@app.get("/")
async def root():
    return JSONResponse(content={"result": "success"})

@app.post("/get-location")
async def create_upload_file(file: UploadFile = File(...)):
    predicted_coords = predict_coords(file.file)

    print('predicted_coords', predicted_coords)
    try:
        relevant_locations = get_location_info(predicted_coords[0][1], predicted_coords[0][0])
    except Exception as e:
        print(e)
        print("Setting relevant locations to []")
        relevant_locations = []
    # Return the processed image as a response
    return JSONResponse(
        content={
            "result": "success", 
            "coords": predicted_coords,
	    "relevant_locations": relevant_locations
        },
        headers={
            'Content-Type': 'application/json',
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*',
        }
    )
    # return {
    #     "status": 200,
    #     "msg": "hello"
    # }
