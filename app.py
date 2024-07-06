import requests
import pprint
from flask import Flask, request, jsonify, render_template
import uuid

app = Flask(__name__)

from bs4 import BeautifulSoup

base_url = "https://parivahan.gov.in"

url = "https://parivahan.gov.in/rcdlstatus/?pur_cd=101"

post_url = "https://parivahan.gov.in/rcdlstatus/vahan/rcDlHome.xhtml"


dl_sessions = {}

# get_data_from_table function takes a table soup object and returns a dictionary
# It takes care of td, tr tags and returns a dictionary with key as the th tag and value as the td tag


def get_data_from_tables(soup):
    data = []
    # Get all the tables
    tables = soup.find_all("table")
    # Loop through all the tables
    for table in tables:
        table_data = {
            "headers": [],
            "data": [],
        }
        # Check if thead exists
        thead = table.find("thead")
        if thead is not None:
            # Get all the th tags
            ths = thead.find_all("th")
            # Loop through all the th tags
            headers = []
            for th in ths:
                headers.append(th.text)
            # Get all the tr tags
            table_data["headers"] = headers

        # Get all the tr tags
        trs = table.find_all("tr")
        # Loop through all the tr tags

        for tr in trs:
            row_data = []
            # Get all the td tags
            tds = tr.find_all("td")
            # Loop through all the td tags
            for i in range(len(tds)):
                row_data.append(tds[i].text)
            table_data["data"].append(row_data)

        data.append(table_data)
    return data


class DL:
    def __init__(self):
        self.post_data = {
            "avax.faces.partial.ajax": "true",
            "javax.faces.source": "form_rcdl:j_idt47",
            "javax.faces.partial.execute": "@all",
            "javax.faces.partial.render": "form_rcdl:pnl_show form_rcdl:pg_show form_rcdl:rcdl_pnl",
            "form_rcdl:j_idt47": "form_rcdl:j_idt47",
            "form_rcdl:tf_dlNO": "HR-3220140048539",
            "form_rcdl:tf_dob_input": "09-12-1995",
            "form_rcdl:j_idt33:CaptchaID": "assas",
            "javax.faces.ViewState": "",
            "form_rcdl": "form_rcdl",
        }
        self.base_url = "https://parivahan.gov.in"
        self.captcha_url = None
        self.page = None
        self.soup = None
        self.id = str(uuid.uuid4())
        self.session = requests.Session()
        self.session.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def initialise(self):
        self.page = self.session.get(url)
        self.soup = BeautifulSoup(self.page.content, "html.parser")
        self.get_default_inputs()

    def get_captcha_url(self):
        # Get the table with class vahan-captcha
        captcha_table = self.soup.find("table", {"class": "vahan-captcha"})
        # Get the img tag
        img = captcha_table.find("img")
        # Get the src attribute
        src = img["src"]
        self.captcha_url = self.base_url + src
        return self.captcha_url

    def get_default_inputs(self):
        form = self.soup.find("form", {"id": "form_rcdl"})
        inputs = form.find_all("input")
        for i in inputs:
            name = ""
            value = ""
            if i.has_attr("name"):
                name = i["name"]
            if i.has_attr("value"):
                value = i["value"]
            if name != "" and value != "":
                self.post_data[name] = value


@app.route("/api/get-captcha", methods=["GET"])
def get_captcha():
    try:
        dl = DL()
        dl.initialise()
        captchaSrc = dl.get_captcha_url()
        dl_sessions[dl.id] = dl
        return jsonify({"captcha": captchaSrc, "id": dl.id})
    except Exception as e:
        print(e)
        return jsonify({"error": "Error getting captcha"})


@app.route("/api/get-vehicle-details", methods=["POST"])
def get_vehicle_details():
    try:
        data = request.json
        id = data["sessionId"]
        dl = dl_sessions[id]
        dl.post_data["form_rcdl:tf_dlNO"] = data["dlno"]
        date = data["dob"]
        # date comes in formay yyyy-mm-dd
        # we need to convert it to dd-mm-yyyy
        date = date.split("-")
        date = date[2] + "-" + date[1] + "-" + date[0]
        print(date)
        dl.post_data["form_rcdl:tf_dob_input"] = date
        dl.post_data["form_rcdl:j_idt33:CaptchaID"] = data["captchaData"]
        response = dl.session.post(post_url, data=dl.post_data)
        soup = BeautifulSoup(response.content, "html.parser")

        print(soup)

        error_messages = []
        try:
            # Find a div with class ui-messages-error-summary
            errors = soup.find_all("span", {"class": "ui-messages-error-summary"})
            print(errors)
            for error in errors:
                if error.text:
                    error_messages.append(error.text)

        except:
            print("Error getting error messages")

        print(error_messages)

        if len(error_messages) > 0:
            return jsonify({"errors": error_messages})

        details = None
        try:
            # Find a div with id form_rcdl:pnl_show
            details = soup.find("div", {"id": "form_rcdl:pnl_show"})
        except:
            pass

        if details is None:
            return jsonify({"error": "Error getting vehicle details"})

        print(str(details))

        return jsonify({"details": get_data_from_tables(details)})
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)})


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
