# Entry point to run the Flask app
import cv2
import numpy as np
import qrcode
import json
import pymongo
from flask import Flask, request, jsonify, render_template
import pyzbar.pyzbar as pyzbar
import os

from app import app

if __name__ == '__main__':
    app.run(debug=True)