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

# find absolute root path (searches for directory containing any of the files on the list)
base_path = pyrootutils.find_root(search_from=__file__, indicator=[".git", "setup.cfg"])


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

@app.post("/get-location")
async def create_upload_file(file: UploadFile = File(...)):
    predicted_coords = predict_coords(file.file)

    print('predicted_coords', predicted_coords)
    
    # Return the processed image as a response
    return JSONResponse(
        content={
            "result": "success", 
            "coords": predicted_coords
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
