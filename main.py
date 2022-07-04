import numpy as np
import firebase_admin
import face_recognition
import cv2
from firebase_admin import credentials, storage
from firebase_admin import firestore
from PIL import Image
import urllib.request
from datetime import datetime, timedelta
import time
from pyzbar.pyzbar import  decode

cred = credentials.Certificate("serviceAccountKey.json")
app = firebase_admin.initialize_app(cred, {'storageBucket': 'test-facenet-e66ef.appspot.com/images'})
images = []
matrics = []
db = firestore.client()
docs_users = db.collection(u'Users').stream()

for doc in docs_users:
    url = doc.to_dict()["imgLink"]
    matric_no = doc.to_dict()['matric']
    print(f'{doc.id} => {url}')
    with urllib.request.urlopen(url) as u:
        with open(f'{matric_no}', 'wb') as f:
            f.write(u.read())
    img = Image.open(f'{matric_no}')
    cvImage = cv2.imread(f'{matric_no}')
    cvImage = cv2.flip(cvImage, 1)
    images.append(cvImage)
    matrics.append(matric_no)
    # cv2.imshow('vertical flip Image', cvImage)
    # cv2.waitKey(0)

    # img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    # img.show()

print (matrics)
# print(images)


def findEncodings(images):
    encodeList = []
    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)[0]
        encodeList.append(encode)
    return encodeList

encodeListKnown = findEncodings(images)
print(len(encodeListKnown))

cap = cv2.VideoCapture(0)

timeout=10


timeout_start = time.time()
regCount = 0
temp = 0
while time.time() < timeout_start + timeout:
    success, img = cap.read()
    imgS = cv2.resize(img, (0,0), None, 0.25,0.25)
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

    facesCurrFrame = face_recognition.face_locations(imgS)
    encodingsCurrFrame = face_recognition.face_encodings(imgS, facesCurrFrame)
    for encodeFace, faceLoc in zip(encodingsCurrFrame, facesCurrFrame):
        matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
        print(matches)
        faceDist = face_recognition.face_distance(encodeListKnown, encodeFace)
        print(faceDist)
        matchIndex = np.argmin(faceDist)
        if matches[matchIndex]:
            print(matchIndex)
            y1,x2,y2,x1 = faceLoc
            y1, x2, y2, x1 = y1*4,x2*4,y2*4,x1*4
            cv2.rectangle(img, (x1,y1),(x2,y2),(0,255,0),2)
            cv2.rectangle(img, (x1,y2-35),(x2,y2),(0,255,0),cv2.FILLED)
            # cv2.putText(img, matric_no,(x1+6,y2-5),cv2.FONT_HERSHEY_COMPLEX,1,(255,255, 255),2)
            matric_result = matrics[matchIndex]
            if (matric_result == temp):
                regCount+=1
            temp = matric_result

            cv2.putText(img, matric_result,(x1+6,y2-5),cv2.FONT_HERSHEY_COMPLEX,1,(255,255, 255),2)
            print (matric_result)

    cv2.imshow('Webcam', img)
    cv2.waitKey(1)

print (temp)


docs_books = db.collection(u'Books').stream()

for doc in docs_books:
    print(f'{doc.id} => {doc.to_dict()["title"]}')
cap = cv2.VideoCapture(0)
print (cap)
cap.set(3,640)
cap.set(4,480)
mydata = ""
timeout=5

timeout_start = time.time()
while time.time() < timeout_start + timeout:
    success, img = cap.read()
    for barcode in decode(img):
        print('here')

        print(barcode.data)
        mydata= barcode.data.decode('utf-8')
        print (mydata)
        pts = np.array([barcode.polygon], np.int32)
        pts = pts.reshape(-1,1,2)
        cv2.polylines(img, [pts],True,(255,0,255), 3)
        pts2 = barcode.rect
        cv2.putText(img, mydata, (pts2[0],pts2[1]),cv2.FONT_HERSHEY_COMPLEX, 0.9, (255,0,255),2)


    cv2.imshow('result', img)
    cv2.waitKey(1)

docs_books = db.collection(u'Books').stream()

book_found = False
book_id = 0
book_copies = 0
for doc in docs_books:
    print ("in book search")
    if (doc.to_dict()['isbn'] == mydata):
        print ("book in db: " + doc.to_dict()['isbn'] + " book found: " + mydata)
        book_found = True
        book_id = doc.id
        book_copies = doc.to_dict()['copies_available']
# docs_books = db.collection(u'Logs').order_by(u'time', direction = firestore.Query.DESCENDING).stream()

docs_logs = db.collection(u'Logs').order_by(u'time', direction = firestore.Query.DESCENDING).stream()
for doc in docs_logs:
    print(f'{doc.id} => {doc.to_dict()["time"]}')


docs_logs = db.collection(u'Logs').order_by(u'time', direction = firestore.Query.DESCENDING).stream()

log_found = False
same_user = False
is_borrow = True
for doc in docs_logs:
    print("USER: " + doc.to_dict()['user'] + "FROM CAM " + str(temp))

    if (doc.to_dict()['book'] == mydata and doc.to_dict()['user'] == temp):
        log_found = True
        is_borrow = doc.to_dict()['is_borrow']



print('MYDATA IS ' + mydata)
# to_insert = {'is_borrow': True, "user": temp, 'book', mydata

if(mydata == "" or temp == ""):
    print ('cannot borrow book, try again')

elif(book_found == False):
    print ('Book not found.')

elif(log_found == True):

    if (is_borrow == True):
      db.collection('Logs').add({'is_borrow': False, 'user': temp, 'book': mydata, 'time': time.time()})
      db.collection('Books').document(book_id).update({"copies_available": book_copies + 1})
      print('Book returned successfully')
    else:
        if (book_copies > 0):
            db.collection('Books').document(book_id).update({"copies_available": book_copies - 1})
            # db.collection('Logs').add({'is_borrow': True, 'user': temp, 'book': mydata})

            db.collection('Logs').add({'is_borrow': True, 'user': temp, 'book': mydata, 'time': time.time()})

            print('Book borrowed successfully')
        else:
            print('Out of Stock')

else:
    if(book_copies > 0):
        db.collection('Books').document(book_id).update({"copies_available": book_copies - 1})
        db.collection('Logs').add({'is_borrow': True, 'user': temp, 'book': mydata, 'time': time.time()})
        print ('Book borrowed successfully')
    else:
        print('Out of Stock')

