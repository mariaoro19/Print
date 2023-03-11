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
import itertools

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
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

#Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.app'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#scheme for the table
class Prints(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    printDate = db.Column(db.DateTime, index=True, default=now_col)
    sheets = db.Column(db.Integer)
    totalPrice = db.Column(db.Integer)
    state = db.Column(db.Integer)
    
    def __repr__(self):
        return '<Print sheets {}>'.format(self.sheets)


#Create database
db.create_all()
#for p in Prints:
#printers = Prints.query.all()
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
    #return render_template('error.html')

#Display and do a Post in the API for choosing the file
@app.route('/', methods=['POST'])
def upload_image():
   
    try:

        if 'file' not in request.files:
            flash('Sin parte del archivo')
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
    except:
        return render_template('error.html', filename=filename,totalpages=totalpages, sizeFile=sizeFile)
                        
    
    
#Function to display file
@app.route('/display/<filename>')
def display_image(filename):
    #print('display_image filename: ' + filename)

    return redirect(url_for('static', filename='uploads/' + filename), code=301)

# Calculate price and save it to the data base
@app.route('/pay/<filename>', methods=['POST','GET'])
def pay(filename):
    try:
        #Get info from the form
        color=request.form.get('color')
        #numCopies=str(request.form.get('numCopies'))
        filepdf='static/uploads/'+filename
        file2 = open(filepdf, 'rb')
        readpdf = PyPDF2.PdfFileReader(file2)
        totalpages = int(readpdf.numPages)
        print("totalpages",totalpages, type(totalpages))
        numCopies=request.form.get('numCopies')
        
        if numCopies ==None:
            numCopies=1
        else:
            numCopies=int(request.form.get('numCopies'))
        
        print("numCopies",numCopies)
        pages=request.form.get('pages')
        #Calculate prices
        if pages == "":
            pages= int(totalpages)
        else:
            # Iterate over the selected characters
            countPages=0
            count=0
            for char in range(0, len(str(pages))):
                if pages[char] != "-" and pages[char].isnumeric() and int(pages[char])<=totalpages:
                    countPages+=1
                elif pages[char] != "-" and pages[char] != "," and pages[char].isnumeric()== False:
                    countPages = 1+totalpages
                    break
                elif pages[char] == ",":
                    countPages=int(pages[char+1])-int(pages[char-1])
                    #print("aqui2",pages[char+1]-pages[char-1])
                elif pages[char] == "-":
                    pass
                #else:
                    #countPages=totalpages+1
                count+=1
                print(pages[char])
            pages=countPages
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

        #Save the info to the database
        p=Prints(sheets=numPagePrinted, totalPrice=totalPrice, state=0)
        db.session.add(p)
        db.session.commit()
        #printers = Prints.query.all()
        #for p in printers:
            #  print(p.id, p.printDate)
        
        #Connect to the printer
        if request.method == 'POST':
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
   
            
        
        #Check for errors
        if pages <=totalpages:
            filesRemove=glob.glob('static/uploads/*')
            #Removing files after print
            for f in filesRemove:
                os.remove(f)
            return render_template('paying.html', totalPrice=totalPrice)
        else:
            flash('Ingreso incorrecto de páginas a imprimir, reintente de nuevo', 'error')
            return render_template('pay.html', filename=filename,totalpages=totalpages, sizeFile=sizeFile)
    except:
        return render_template('error.html', filename=filename,totalpages=totalpages, sizeFile=sizeFile)

# Connecting to the localhost
if __name__ == '__main__':
   
   app.run(debug=True, port=3003, host='192.168.1.21')
   #app.run(debug=True, port=3003, host='127.0.0.2')
   
   #app.config['SERVER_NAME']= "printexp.dev:3003"
   #app.url_map.host_matching=True
   #app.run(debug=True, host='printexp.dev:3003')
   