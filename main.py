# Libreries

import os
import cups
from flask import Flask, session, flash, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
import PyPDF2
import glob
import subprocess
import time
from datetime import datetime
from sqlalchemy import select
from pytz import timezone
import pytz

format = "%Y-%m-%d %H:%M:%S %Z%z"
# Current time in UTC
now_utc = datetime.now(timezone('UTC'))
now_col = now_utc.astimezone(timezone('America/Bogota'))
#print(now_col.strftime(format))

#Variables
UPLOAD_FOLDER = 'static/uploads/'

basedir = os.path.abspath(os.path.dirname(__file__))

# Initialing API
app = Flask(__name__)
app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Initialing database
#from app.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

#app = Flask(__name__)
#app.config.from_object(Config)
#SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
 #       'sqlite:///' + os.path.join(basedir, 'app.db')
#SQLALCHEMY_TRACK_MODIFICATIONS = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.app'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 


db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Prints(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    printDate = db.Column(db.DateTime, index=True, default=now_col)
    sheets = db.Column(db.Integer)
    totalPrice = db.Column(db.Integer)
    state = db.Column(db.Integer)
    
    def __repr__(self):
        return '<Print sheets {}>'.format(self.sheets)


#from app import models
db.create_all()
#p=Prints(sheets=2, totalPrice=2000, state=0)
#db.session.add(p)
#db.session.commit()

#for p in Prints:
printers = Prints.query.all()
#for p in printers:
 #    print(p.id, p.printDate)

#Formats of files allowed to print
#ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif', 'pdf'])
ALLOWED_EXTENSIONS = set([ 'pdf'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Display the main page
@app.route('/')
def upload_form():
    return render_template('upload.html')

#Display and do a Post in the API for choosing the file
@app.route('/', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No ha seleccionado archivo','error')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        if filename.rsplit('.', 1)[1].lower() == 'pdf':
            filepdf='static/uploads/'+filename
            file2 = open(filepdf, 'rb')
            readpdf = PyPDF2.PdfFileReader(file2)
            totalpages = readpdf.numPages
            countLetter=0
            countLegal=0
            sizeFileVector=[]
            #Loop to check the bigger page
            for i in range(totalpages):
                sizeFileV = readpdf.getPage(i).mediaBox
                print(sizeFileV[3])
                sizeFileVector.append(sizeFileV)
            sizeFileV= max(sizeFileVector)
            
            # We have that Letter is 612x792 and Legal is 612x939
            if sizeFileV[3]>792:
                #sizeFile="Custom.612x936"
                sizeFile="Legal"
                session['size'] = sizeFile
                flash('Imagen cargada exitosamente')
                #print(totalpages)
                return render_template('pay.html', filename=filename,totalpages=totalpages, sizeFile=sizeFile)
            elif sizeFileV[2]>612 and sizeFileV[3]>936: 
                flash('Tamaño del documento deben ser Carta u Oficio', 'error')
                return redirect(request.url)
            else:
                sizeFile="Letter"
                session['size'] = sizeFile
                flash('Imagen cargada exitosamente')
                print(totalpages)
                return render_template('pay.html', filename=filename,totalpages=totalpages, sizeFile=sizeFile)
                    
            
        #For now this else doesn work, its for images
        else:
            totalpages = 1
            sizeFile="Letter"   
    
    else:
        flash('Formato del documento no admitido', 'error')
        return redirect(request.url)
    
    
#Function to display file
@app.route('/display/<filename>')
def display_image(filename):
    #print('display_image filename: ' + filename)

    return redirect(url_for('static', filename='uploads/' + filename), code=301)

# # Printing after uploading the file	
#@app.route('/pay/<filename>', methods=['GET','POST'])
@app.route('/pay/<filename>', methods=['POST','GET'])
def pay(filename):
   
   color=request.form.get('color')
   #numCopies=str(request.form.get('numCopies'))
   filepdf='static/uploads/'+filename
   file2 = open(filepdf, 'rb')
   readpdf = PyPDF2.PdfFileReader(file2)
   totalpages = int(readpdf.numPages)
   print("totalpages",totalpages, type(totalpages))
   numCopies=int(request.form.get('numCopies'))
   if numCopies ==None:
    numCopies=1
   print("numCopies",numCopies)
   pages=request.form.get('pages')
   if pages == "":
    pages= int(totalpages)
   print("pages",pages,type(pages))
   sides= request.form.get('side')
   
   numPagePrinted = totalpages * numCopies	
   sizeFile = session.get('size', None)
   color=request.form.get('color')
   if sizeFile == "Letter" and color == "monochrome" and sides == "one-sided":
    totalPrice =80*numCopies*pages
   elif sizeFile == "Letter" and color == "monochrome" and sides == "DuplexTumble":
    totalPrice =70*numCopies*pages
   elif sizeFile == "Legal" and color == "monochrome" and sides == "one-sided":
    totalPrice =100*numCopies*pages
   elif sizeFile == "Legal" and color == "monochrome" and sides == "DuplexTumble":
    totalPrice =90*numCopies*pages
   else:
    totalPrice =200*numCopies*pages

   p=Prints(sheets=numPagePrinted, totalPrice=totalPrice, state=0)
   print("Total price",totalPrice, "numCopies", numCopies)
   db.session.add(p)
   db.session.commit()
   #printers = Prints.query.all()
   #for p in printers:
       #  print(p.id, p.printDate)
   
   if request.method == 'POST':
   #else:
       #f = request.files['file']
       #f.save(secure_filename(f.filename))
       conn = cups.Connection ()
       printers = conn.getPrinters ()
       #print('printer',printers)
       for printer in printers:
           print ("printer:"+printer, printers[printer]["device-uri"])
           printer_name=printer
       #print(f.filename)
       #file =f.filename
       file="static/uploads/"+filename
       #print(file)
      
       #conn.printFile (printer_name, file, "Project Report", {"Duplex":"DuplexTumble"}) 
    
    #    if pages=="":
            
    #       printid = conn.printFile (printer_name, file, "Project Report", {"print-color-mode":color,"copies":numCopies,"sides":sides, "media":sizeFile}) 
    #    else:

    #       printid= conn.printFile (printer_name, file, "Project Report", {"print-color-mode":color,"copies":numCopies,"sides":sides, "media":sizeFile,"page-ranges":pages}) 
       
          
       
   #print(printid)
   #printjob=conn.getJobAttributes(printid)["job-state"]
   #printid = conn.printFile(printer_name, file, 'test', {})
   #Checking if the print was suscessfull
   #print(printid)
   #print(printjob)
   stop = 0
   TIMEOUT = 50
    
#    while str(subprocess.check_output(["lpstat"])).find(str(printid)) > 0 and    stop < TIMEOUT:
#        stop+= 1
#        time.sleep(1)
#    if stop < TIMEOUT:
#        print ("PRINT SUCCESS")
#    else:
#        print ("PRINT FAILURE")

   #Removing files after print
   

   if pages <=totalpages:
    filesRemove=glob.glob('static/uploads/*')
    for f in filesRemove:
       os.remove(f)
    return render_template('payProcess.html')
   else:
    flash('Ingreso incorrecto de páginas a imprimir', 'error')
    return redirect(request.url)

# Connecting to the localhost
if __name__ == '__main__':
   
   app.run(debug=True, port=3002, host='192.168.1.21')
   #app.run(debug=True, port=3003, host='127.0.0.2')
   
   #app.config['SERVER_NAME']= "printexp.dev:3003"
   #app.url_map.host_matching=True
   #app.run(debug=True, host='printexp.dev:3003')
   