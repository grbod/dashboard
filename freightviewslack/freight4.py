# from os import PRIO_PROCESS, write
import requests
import config
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from tabulate import tabulate
from pydatamodel import *
import logging
from pydantic import ValidationError

# Configure the logging module to save logs to a file
logging.basicConfig(filename='error.log', level=logging.ERROR, format='%(asctime)s [%(levelname)s] - %(message)s')
logger = logging.getLogger()

SLACK_TOKEN = config.SLACK_TOKEN
client = WebClient(token=SLACK_TOKEN)


def post_to_slack(title,message):
    code_block_message = f"```{title}\n\n{message}```"  # Wrap the message in triple backticks for a code block
    try:
        response = client.chat_postMessage(channel='#shipping', text=code_block_message)
    except SlackApiError as e:
        print(f"Error posting to Slack: {e}")

def write_to_slack(message):
    try:
        response = client.chat_postMessage(channel='#shipping', text=message)
    except SlackApiError as e:
        print(f"Error posting to Slack: {e}")

def get_API_auth():
    # API endpoint (replace with the actual endpoint from the documentation)
    TOKEN_URL = "https://api.freightview.com/v2.0/auth/token"

    # Payload from the documentation
    payload = {
        "client_id": config.CLIENT_ID,
        "client_secret": config.CLIENT_SECRET,
        "grant_type": "client_credentials"
    }

    # Make the POST request
    response = requests.post(TOKEN_URL, json=payload)

    # check if the request was successful
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get("access_token")
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        print("Access Token Obtained!")
        return(headers)
    else:
        print(f"Failed to get token. Status code: {response.status_code}, Message: {response.text}")
        exit()


def extract_inbound(model: Model):
    table_data = []
    for shipment in model.shipments:
        print(shipment.shipmentId)
        if(shipment.direction=="inbound"):
            consignee = shipment.locations[0].company[:15]
            ponum = shipment.locations[1].refNums[0].value
            if shipment.tracking.deliveryDateEstimate is not None:
                deliverydateestimate = shipment.tracking.deliveryDateEstimate.date()
            else:
                deliverydateestimate = "N/A"  # or some default value
            lastupdate = shipment.tracking.lastUpdatedDate.date()
            carriername = shipment.selectedQuote.assetCarrierName[:15]
            tracking = shipment.tracking.trackingNumber
            # Create a dictionary for each shipment and append it to the list
            table_data.append({
                "Consignee": consignee,
                "PO Number": ponum,
                "Delivery Est": deliverydateestimate,
                "Last Update": lastupdate,
                "Carrier Name": carriername,
                "Tracking": tracking
            })
            try:
                price = shipment.selectedQuote.amount
                weight = shipment.equipment.weight
                weightUOM  = shipment.equipment.weightUOM
                cost_per_lb = round(price / weight, 2)
                message = f"PO {ponum} | Price: {price} | Weight: {weight}{weightUOM} | Cost per lb: ${cost_per_lb}"
                write_to_slack(message)
                print(message)
            except AttributeError:
                pass 
    # Use tabulate to print the table
    table_data = tabulate(table_data, headers="keys", tablefmt="heavy_outline")
    if not table_data:
        return "NO INBOUND DATA"
    return table_data

def extract_outbound(model: Model):
    table_data = []
    for shipment in model.shipments:
        print(shipment.shipmentId)
        if(shipment.direction=="outbound"):
            consignor = shipment.locations[1].company[:15]
            try:
                invnum = shipment.locations[0].refNums[0].value
            except IndexError:
                invnum = "N/A"
            if shipment.tracking.deliveryDateEstimate is not None:
                deliverydateestimate = shipment.tracking.deliveryDateEstimate.date()
            else:
                deliverydateestimate = "N/A"  # or some default value
            lastupdate = shipment.tracking.lastUpdatedDate.date()
            try:
                carriername = shipment.selectedQuote.assetCarrierName[:15]
            except TypeError:
                carriername = "Unknown"
            tracking = shipment.tracking.trackingNumber
            email = shipment.locations[1].contactEmail
            
            # Create a dictionary for each shipment and append it to the list
            table_data.append({
                "Consignor": consignor,
                "Inv Number": invnum,
                "Delivery Est": deliverydateestimate,
                "Last Update": lastupdate,
                "Carrier Name": carriername,
                "Tracking": tracking
            })
            try:
                price = shipment.selectedQuote.amount
                weight = shipment.equipment.weight
                weightUOM = shipment.equipment.weightUOM
                cost_per_lb = round(price / weight, 2)
                message = f"Customer {consignor} | Price: {price} | Weight: {weight}{weightUOM} | Cost per lb: ${cost_per_lb}"
                write_to_slack(message)
                print(message)
            except AttributeError:
                pass 
    if not table_data:
        return "NO OUTBOUND DATA"
    # Use tabulate to print the table
    table_data = tabulate(table_data, headers="keys", tablefmt="heavy_outline")
    return table_data 

def other_sched_pickups(headers):
    url = "https://api.freightview.com/v2.0/shipments?status=pending&status=awarded"
    print(url)
    response = requests.get(url, headers=headers)
    data = response.json()
    try:
        model = Model.model_validate(data)
        table_data = []
        # iternate through model object, printing the shipmentID
        for shipment in model.shipments:
            print(shipment.status)
            print("hi")
    except:
        print("fail")
        pass




def main(): 
    #check if the API request was successful 
    headers = get_API_auth() 
    # GET PICKED UP API REQUEST 
    url = "https://api.freightview.com/v2.0/shipments?status=picked-up" 
    response = requests.get(url, headers=headers) 
    data = response.json() 
    try:
        model = Model.model_validate(data) 
        # inbound_table = extract_inbound(model)
        # post_to_slack("INBOUND FREIGHT",inbound_table)
        # outbound_table = extract_outbound(model)
        # post_to_slack("OUTBOUND FREIGHT",outbound_table)
    except ValidationError as e:
        error_details = e.errors()
        error_summary = "\n".join([
            f"Field: {error['loc'][0]}, Error: {error['msg']}, Provided value: {error['value']}"
            for error in error_details
        ])
        print(error_summary)
        logger.error("Pydantic validation error details:\n%s", error_summary)
        logger.exception("Full traceback:")

    # GET PENDING & AWARDED TO SEE IF MAYBE SOMETHING MISSED PICK-UP
    other_sched_pickups(headers) 

    # # GET PENDING UP API REQUEST
    # url = "https://api.freightview.com/v2.0/shipments?status=confirmed"
    # response = requests.get(url, headers=headers)
    # data = response.json()
    # pending_df = extract_shipment_data(data)
    # print(pending_df)
    

    # OUTBOUND TABLE PROCESSING 
    # outbound_filtered_df = df.loc[df['Direction'] == "outbound"]
    # outbound_filtered_df = outbound_filtered_df.drop(columns=['ShipmentID','DeliveryDateActual','Status','PickupDate','Direction','FirstCompany','FirstAddress','SecondAddress','City','State','PostalCode','PickupDateActual'])

    # print(outbound_filtered_df)
    # tablemsg = tabulate(outbound_filtered_df, headers='keys', tablefmt='heavy_outline')
    # post_to_slack("OUTBOUND FREIGHT IN-TRANSIT",tablemsg)




if __name__ == "__main__":
    # This code will only run if the script is executed directly
    print("The script is being run directly.")
    main()


