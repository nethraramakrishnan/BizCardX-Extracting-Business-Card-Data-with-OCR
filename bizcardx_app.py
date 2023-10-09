import os
import re
import mysql.connector as sql
import easyocr
import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_option_menu import option_menu

# Setting Up Page Configuration
icon = Image.open("icon.png")
st.set_page_config(page_title= "BizCardX: Extracting Business Card Data with OCR | By NETHRA R",
                   page_icon= icon,
                   layout= "wide")
st.markdown("<h1 style='text-align: center; color: red;'>BizCardX: Extracting Business Card Data with OCR</h1>", unsafe_allow_html=True)

def setting_bg():
    st.markdown(f""" <style>.stApp {{
                        background: url("https://cutewallpaper.org/21x/4ol958vig/76+-Light-Blue-Backgrounds-on-WallpaperSafari.jpg");
                        background-size: cover}}
                     </style>""",unsafe_allow_html=True)
setting_bg()


#Creating Option Menu
selected = option_menu(None, ["Home","Upload & Extract","Modify"],
                       icons=["house","cloud-upload","pencil-square"],
                       default_index=0,
                       orientation="horizontal",
                       styles={"nav-link": {"font-size": "35px", "text-align": "centre"},
                               "icon": {"font-size": "35px"}})


# CONNECTING WITH MYSQL DATABASE
mydb = sql.connect(host="localhost",
                   user="root",
                   password="password",
                   database= "bizcard"
                  )
mycursor = mydb.cursor(buffered=True)


# TABLE CREATION
mycursor.execute('''CREATE TABLE IF NOT EXISTS card_data
                   (id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    company_name TEXT,
                    card_holder TEXT,
                    designation TEXT,
                    mobile_number VARCHAR(50),
                    email TEXT,
                    website TEXT,
                    area TEXT,
                    city TEXT,
                    state TEXT,
                    pin_code VARCHAR(10),
                    image LONGBLOB
                    )''')


# Initializing EasyOCR
reader = easyocr.Reader(['en'])

if selected == 'Home':
    col1, col2 = st.columns(2)
    with col1:
        st.image("OCR.png")
    with col2:
        st.markdown("### :red[**Technologies Used :**] Python,easy OCR, Streamlit, SQL, Pandas")
        st.markdown("### :red[**Overview :**] In this streamlit web app you can upload an image of a business card and extract relevant information from it using easyOCR. You can view, modify or delete the extracted data in this app. This app would also allow users to save the extracted information into a database along with the uploaded business card image. The database would be able to store multiple entries, each with its own business card image and extracted information.")


if selected == 'Upload & Extract':
    st.markdown("## :red[Upload a Business Card]")
    uploaded_card = st.file_uploader("upload here", label_visibility="collapsed", type=["png", "jpeg", "jpg"])

    if uploaded_card is not None:
        col1,col2,col3 = st.columns(3)
        with col1:
            st.markdown("#    ")
        with col2:
             # DISPLAYING THE UPLOADED CARD
            st.markdown("#     ")
            st.markdown("## :green[You have uploaded the card]")
            st.image(uploaded_card)
        with col3:
            st.markdown("#    ")

        with st.spinner("Please wait processing image..."):
            #easy OCR
            saved_img = os.getcwd()+ "\\" + "uploaded_cards"+ "\\"+ uploaded_card.name
            result = reader.readtext(saved_img,detail = 0,paragraph=False)


        # CONVERTING IMAGE INTO BINARY AND UPLOAD IT INTO SQL DATABASE
        def img_to_binary(file):
            # Convert image data to binary format
            with open(file, 'rb') as file:
                binaryData = file.read()
            return binaryData


        data = {"company_name": [],
                "card_holder": [],
                "designation": [],
                "mobile_number": [],
                "email": [],
                "website": [],
                "area": [],
                "city": [],
                "state": [],
                "pin_code": [],
                "image": img_to_binary(saved_img)
                }

        #Fetching/parsing the data from EasyOCR response
        def get_data(res):
            for ind, i in enumerate(res):
                #Fetch the Company Name
                if ind == len(res)-1:
                    data["company_name"].append(i)
                #Fetch the Cardholder Name
                elif ind == 0:
                    data["card_holder"].append(i)
                #Fetch the Designation
                elif ind == 1:
                    data["designation"].append(i)
                #Fetch the WEBSITE_URL
                elif "www " in i.lower() or "www." in i.lower():
                    data["website"].append(i)
                elif "WWW" in i:
                    data["website"] = res[4] + "." + res[5]
                #Fecth the EMAIL ID
                elif "@" in i:
                    data["email"].append(i)
                #Fetch the  MOBILE NUMBER
                elif "-" in i:
                    data["mobile_number"].append(i)
                    if len(data["mobile_number"]) == 2:
                        data["mobile_number"] = " & ".join(data["mobile_number"])
                #Fetch the AREA
                if re.findall('^[0-9].+, [a-zA-Z]+', i):
                    data["area"].append(i.split(',')[0])
                elif re.findall('[0-9] [a-zA-Z]+', i):
                    data["area"].append(i)
                #Fetch the CITY NAME
                match1 = re.findall('.+St , ([a-zA-Z]+).+', i)
                match2 = re.findall('.+St,, ([a-zA-Z]+).+', i)
                match3 = re.findall('^[E].*',i)
                if match1:
                    data["city"].append(match1[0])
                elif match2:
                    data["city"].append(match2[0])
                elif match3:
                    data["city"].append(match3[0])
                #Fetch the STATE
                state_match = re.findall('[a-zA-Z]{9} +[0-9]',i)
                if state_match:
                     data["state"].append(i[:9])
                elif re.findall('^[0-9].+, ([a-zA-Z]+);',i):
                    data["state"].append(i.split()[-1])
                if len(data["state"])== 2:
                    data["state"].pop(0)
                #Fetch the PINCODE
                if len(i)>=6 and i.isdigit():
                    data["pin_code"].append(i)
                elif re.findall('[a-zA-Z]{9} +[0-9]',i):
                    data["pin_code"].append(i[10:])

        #CALLING THE METHOD TO PARSE THE DATA FROM EASYOCR RESPONSE AND STORING INTO THE VARIABLE CALLED "DATA"
        get_data(result)


        # FUNCTION TO CREATE DATAFRAME
        def create_df(data):
            df = pd.DataFrame(data)
            return df


        df = create_df(data)
        st.success("## :green[Data Extracted!]")
        st.write(df)

        if st.button("  :green[Upload to Database]"):
            for i, row in df.iterrows():
                # here %S means string values
                sql = """INSERT INTO card_data(company_name,card_holder,designation,mobile_number,email,website,area,city,state,pin_code,image)
                                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
                mycursor.execute(sql, tuple(row))
                # the connection is not auto committed by default, so we must commit to save our changes
                mydb.commit()
            st.success("## Uploaded to database successfully!")

# MODIFY MENU
if selected == "Modify":
    col1, col2, col3 = st.columns([3, 3, 2])
    col2.markdown("## :red[Modify the Data]")
    column1, column2 = st.columns(2, gap="large")
    try:
        with column1:
            mycursor.execute("SELECT card_holder FROM card_data")
            result = mycursor.fetchall()
            business_cards = {}
            for row in result:
                business_cards[row[0]] = row[0]
            selected_card = st.selectbox(":red[Select a card holder name to update]", list(business_cards.keys()))
            st.markdown("### Update or modify any data below")
            mycursor.execute(
                "select company_name,card_holder,designation,mobile_number,email,website,area,city,state,pin_code from card_data WHERE card_holder=%s",
                (selected_card,))
            result = mycursor.fetchone()

            # DISPLAYING ALL THE INFORMATIONS
            company_name = st.text_input("Company_Name", result[0])
            card_holder = st.text_input("Card_Holder", result[1])
            designation = st.text_input("Designation", result[2])
            mobile_number = st.text_input("Mobile_Number", result[3])
            email = st.text_input("Email", result[4])
        with column2:
            st.markdown("###      ")
            st.markdown("###      ")
            st.markdown("###      ")
            website = st.text_input("Website", result[5])
            area = st.text_input("Area", result[6])
            city = st.text_input("City", result[7])
            state = st.text_input("State", result[8])
            pin_code = st.text_input("Pin_Code", result[9])

            if st.button("Commit changes to DB"):
                # Update the information for the selected business card in the database
                mycursor.execute("""UPDATE card_data SET company_name=%s,card_holder=%s,designation=%s,mobile_number=%s,email=%s,website=%s,area=%s,city=%s,state=%s,pin_code=%s
                                    WHERE card_holder=%s""", (
                company_name, card_holder, designation, mobile_number, email, website, area, city, state, pin_code,
                selected_card))
                mydb.commit()
                st.success("Information updated in database successfully.")

        if st.button("View updated data"):
            mycursor.execute("select company_name,card_holder,designation,mobile_number,email,website,area,city,state,pin_code from card_data")
            updated_df = pd.DataFrame(mycursor.fetchall(), columns=["Company_Name", "Card_Holder", "Designation", "Mobile_Number",
                                                   "Email","Website", "Area", "City", "State", "Pin_Code"])
            st.write(updated_df)

        coll1,coll2,coll3 = st.columns([3,3,2])
        with coll2:
            coll2.markdown("## :red[Delete the Data]")
        mycursor.execute("SELECT card_holder FROM card_data")
        result = mycursor.fetchall()
        business_cards = {}
        for row in result:
            business_cards[row[0]] = row[0]
        selected_card = st.selectbox("Select a card holder name to Delete", list(business_cards.keys()))
        st.write(f"### You have selected :green[**{selected_card}'s**] card to delete")
        st.write("#### Proceed to delete this card?")

        if st.button("Yes Delete Business Card"):
            mycursor.execute(f"DELETE FROM card_data WHERE card_holder='{selected_card}'")
            mydb.commit()
            st.success("Business card information deleted from database.")
    except:
        st.warning("There is no data available in the database")




