import os
import numpy as np
import cv2
import subprocess as sp
import shutil
from flask import Flask, render_template, request, send_file, send_from_directory

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = set(['png','webm', 'mkv', 'flv', 'vob', 'ogv', 'ogg', 'drc', 'gif', 'gifv', 'mng', 'avi', 'mov', 'qt', 'wmv', 'rm', 'rmvb', 'asf', 'mp4', 'm4p', 'm4v', 'mpg', 'mp2', 'mpeg', 'mpe', 'mpv', 'm2v', 'm4v', 'svi', '3gp', '3g2', 'mxf', 'roq', 'nsv', 'flv', 'f4v', 'f4p', 'f4a', 'f4b', 'yuv']) # https://en.wikipedia.org/wiki/Video_file_format

# Initialize the Flask application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024 # File size limit = 100M

def hologram(infile, outfile, screen_below_pyramid=False):
    '''Transform infile video to a hologram video with no audio track and save to outfile'''
    capture = cv2.cv.CaptureFromFile(infile)
    # nbFrames = int(cv2.cv.GetCaptureProperty(capture, cv2.cv.CV_CAP_PROP_FRAME_COUNT))
    width = int(cv2.cv.GetCaptureProperty(capture, cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
    height = int(cv2.cv.GetCaptureProperty(capture, cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
    fps = cv2.cv.GetCaptureProperty(capture, cv2.cv.CV_CAP_PROP_FPS)
    # duration = (nbFrames / float(fps))

    length = request.form['length']
    d = request.form['d']
    padding = request.form['padding']
    assert 0 < int(length) <= 5000, 'Length is not in (0, 5000].'
    assert 0 < int(d) < int(length) / 2, 'd is not in (0, length/2).'
    assert 0 <= 2 * int(padding) < min(2 * int(d), int(length) / 2 - int(d)), 'Padding is too large.'
    length, d, padding = map(int, [length, d, padding])
    if length % 2:
        length += 1 # Keep length even for convenience
    cap = cv2.VideoCapture(infile)
    bgd = np.zeros((length, length, 3), np.uint8) # Create a black background
    new_wid = 2 * d - 2 * padding
    new_hgt = int(float(new_wid) / width * height)
    if new_hgt + d + 2 * padding > length / 2:
        new_hgt = length / 2 - d - 2 * padding
        new_wid = int(float(new_hgt) / height * width)
    if new_wid % 2:
        new_wid -= 1
    if new_hgt % 2:
        new_hgt -= 1

    fourcc = cv2.cv.CV_FOURCC('m', 'p', '4', 'v')
    out = cv2.VideoWriter(outfile, fourcc, fps, (length,length))

    while(1):
        ret, frame = cap.read()
        if not ret:
            break
        resized_frame = cv2.resize(frame, (new_wid, new_hgt))
        if screen_below_pyramid:
            resized_frame = cv2.flip(resized_frame, 0)
        bgd[length/2 + d + padding:length/2 + d + new_hgt + padding, length/2 - new_wid/2:length/2 + new_wid/2] =\
            resized_frame
        bgd[length/2 - d - padding - new_hgt:length/2 - d - padding, length/2 - new_wid/2:length/2 + new_wid/2] =\
            cv2.flip(resized_frame, -1)
        bgd[length/2 - new_wid/2:length/2 + new_wid/2, length/2 + d + padding:length/2 + d + new_hgt + padding] =\
            cv2.flip(cv2.transpose(resized_frame), 0)
        bgd[length/2 - new_wid/2:length/2 + new_wid/2, length/2 - d - padding - new_hgt:length/2 - d - padding] =\
            cv2.flip(cv2.transpose(resized_frame), 1)
        out.write(bgd)

    cap.release()
    out.release()

def allowed_file(filename):
    return '.' in filename and \
           filename.split('.', 1)[-1] in ALLOWED_EXTENSIONS

# Define a route for the default URL, which loads the form
@app.route('/')
def form():
    return render_template('form_submit.html')

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            shutil.rmtree(UPLOAD_FOLDER)
            os.makedirs(UPLOAD_FOLDER)
            filename = 'original_video.' + file.filename.split('.', 1)[-1]
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            upsidedown = 'upsidedown' in request.form
            hologram(filepath, UPLOAD_FOLDER + 'video_noaudio.avi', screen_below_pyramid=upsidedown)
            sp.call(['avconv', '-y', '-i', UPLOAD_FOLDER + 'video_noaudio.avi', '-i', filepath, '-c', 'copy', '-map', '0:0', '-map', '1:1', UPLOAD_FOLDER + 'out.mkv']) # Add audio track
            return send_from_directory(app.config['UPLOAD_FOLDER'], 'out.mkv', as_attachment=True)
    return form()

# Run the app :)
if __name__ == '__main__':
  app.run(debug=True)
