# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import ask_sdk_core.utils as ask_utils
import os
import boto3

from boto3.dynamodb.conditions import Key
from ask_sdk_s3.adapter import S3Adapter
s3_adapter = S3Adapter(bucket_name=os.environ["S3_PERSISTENCE_BUCKET"])

from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

################################## imported ###############################
from datetime import date
import datetime
from random import seed
from random import randint

################################## class ################################## 

class DBStorage():
    DB_ID = #Your database ID
    DB_KEY = #Your database KEY
    def get_exp_date_str(date, food):
        return_val = {"type":"", "val":""}
        client = boto3.resource('dynamodb',aws_access_key_id=DBStorage.DB_ID, aws_secret_access_key=DBStorage.DB_KEY, region_name='us-east-2')
        table = client.Table('food_name')
        response = table.get_item(Key={'food_name': food})
        if (len(response) == 1):
            try: # connect secondary server
                table = client.Table('users_created')
                response = table.query(
                    KeyConditionExpression=Key('food_name').eq(food)
                )
                response = sorted(response['Items'], key = lambda x: int(x['vote']), reverse = True)[0]
                expiration = int(response['duration'])
                base_date = datetime.datetime.strptime(date, "%Y-%m-%d")
                exp_date = base_date + datetime.timedelta(days=expiration)
                exp_date_str = exp_date.strftime("%Y-%m-%d")
                print(response['vote'])
                if (int(response['vote']) > 0):
                    return_val = {"type" : "sys", "val": exp_date_str}
                else:
                    return_val = {"type" : "bad", "val" : ""}
            except Exception as e:
                return_val = {"type" : "bad", "val" : ""}
            return return_val
        else:
            food_category = response['Item']['category']
            table = client.Table('duration')
            response = table.get_item(Key={'category': food_category})
            expiration = int(response['Item']['fridge'])
            base_date = datetime.datetime.strptime(date, "%Y-%m-%d")
            exp_date = base_date + datetime.timedelta(days=expiration)
            exp_date_str = exp_date.strftime("%Y-%m-%d")
            return_val = {"type" : "sys", "val": exp_date_str}
            return return_val

    def set_duration_dur(duration, food):
        duration = str(duration)
        client = boto3.resource('dynamodb',aws_access_key_id=DBStorage.DB_ID, aws_secret_access_key=DBStorage.DB_KEY, region_name='us-east-2')
        table = client.Table('users_created') #secondary table
        response = table.get_item(Key={'food_name': food, 'duration': duration})
        if (len(response) == 1):
            table.put_item(
                Item={
                    'food_name': food,
                    'duration': duration,
                    'vote': '1',
                }
            )
        else:
            try:
                vote = str(int(response['Item']['vote']) + 1)
                table.update_item(
                    Key={
                        'food_name': food,
                        'duration': duration,
                    },
                    UpdateExpression='SET vote = :val1',
                    ExpressionAttributeValues={
                        ':val1': vote
                    }
                )
            except Exception as e:
                return False
        return True

class Storage():
    def __init__(self, attr_manager):
        self.internal_arr = {}
        self.manager = attr_manager
        temp = self.manager.persistent_attributes
        if (len(temp) != 0):
            self.internal_arr = temp
 
    def set_exp(self, food_name, exp_date):
        if (food_name not in self.internal_arr):
            return False
        self.internal_arr[food_name]["exp_date"] = exp_date
        self.manager.persistent_attributes = self.internal_arr
        self.manager.save_persistent_attributes()
        return True
 
    def add_food(self, food_name, exp_date, in_fridge):
        return_flag = True
        if (food_name in self.internal_arr):
            return_flag = False
        self.internal_arr[food_name] = {"exp_date": exp_date, "fridge": in_fridge}
        self.manager.persistent_attributes = self.internal_arr
        self.manager.save_persistent_attributes()
        return return_flag
    
    def delete_food(self, food_name):
        if (food_name not in self.internal_arr):
            return False
        self.internal_arr.pop(food_name, None)
        self.manager.persistent_attributes = self.internal_arr
        self.manager.save_persistent_attributes()
        return True
 
    def get_exp_date(self, food_name):
        if (food_name not in self.internal_arr):
            return ""
        return self.internal_arr[food_name]["exp_date"]
 
    def get_all(self):
        return self.internal_arr
    	
################################## launch request ################################## 

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        pantry = Storage(handler_input.attributes_manager)
        food_pq = pantry.get_all()
        speak_output = ""
        
        if not bool(food_pq):
            speak_output = """Welcome to your pantry, where you could manage all your food and view what is expiring. 
            To add or remove up to two items in a sentence, say something like I bought apples yesterday or I cooked the steak. 
            Say what's in my pantry to see what is expiring."""
        else:
            pantry = Storage(handler_input.attributes_manager)
    
            speak_output = ""
        
            sorted_food_pq = sorted(food_pq.items(), key = lambda x: x[1]['exp_date'], reverse = False)
            
            if len(sorted_food_pq) <= 5:
                speak_output = "Here's your top " + str(len(sorted_food_pq)) + " expiring food: "
                
                for i in sorted_food_pq:
                    now_time_obj = datetime.datetime.strptime(i[1]['exp_date'], '%Y-%m-%d')
                    day_diff =  (now_time_obj - datetime.datetime.now()).days
                    speak_output = speak_output + i[0] + " expiring in " + str(day_diff) + " days, "
                
            else:
                speak_output = "Here's your top 5 expiring food: "
                for i in range(0, 4):
                    now_time_obj = datetime.datetime.strptime(sorted_food_pq[i][1]['exp_date'], '%Y-%m-%d')
                    day_diff =  (now_time_obj - datetime.datetime.now()).days
                    speak_output = speak_output + sorted_food_pq[i][0] + " expiring in " + str(day_diff) + " days, "
                        
            speak_output = "Welcome to pantry, " + speak_output
        
            for food in sorted_food_pq:
                now_time_obj = datetime.datetime.strptime(food[1]["exp_date"], '%Y-%m-%d')
                day_diff =  (now_time_obj - datetime.datetime.now()).days
                if day_diff < 0:
                    delete_food = pantry.delete_food(food[0])
                    speak_output = speak_output + " your " + food[0] + " is expired and removed from your pantry. "
                
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

################################## I want to see what's in my pantry ################################## 

class ViewIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ViewIntent")(handler_input)
        
    def handle(self, handler_input): 
        pantry = Storage(handler_input.attributes_manager)
        
        food_pq = pantry.get_all()
        
        speak_output = ""
        
        if bool(food_pq):
            sorted_food_pq = sorted(food_pq.items(), key = lambda x: x[1]['exp_date'], reverse = False)
            
            if len(sorted_food_pq) <= 5:
                speak_output = "Here's your top " + str(len(sorted_food_pq)) + " expiring food: "
                
                for i in sorted_food_pq:
                    now_time_obj = datetime.datetime.strptime(i[1]['exp_date'], '%Y-%m-%d')
                    day_diff =  (now_time_obj - datetime.datetime.now()).days
                    speak_output = speak_output + i[0] + " expiring in " + str(day_diff) + " days, "
                
            else:
                speak_output = "Here's your top 5 expiring food: "
                for i in range(0, 4):
                    now_time_obj = datetime.datetime.strptime(sorted_food_pq[i][1]['exp_date'], '%Y-%m-%d')
                    day_diff =  (now_time_obj - datetime.datetime.now()).days
                    speak_output = speak_output + sorted_food_pq[i][0] + " expiring in " + str(day_diff) + " days, "
                
        else:
            speak_output = "Your pantry is empty"
            
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

################################## I want to add what's in my pantry ################################## 

class AddIntentHandler(AbstractRequestHandler):
    """Handler for Add Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AddIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = ""

        # type: (HandlerInput) -> Response
        pantry = Storage(handler_input.attributes_manager)
        slots = handler_input.request_envelope.request.intent.slots
        
        food_first = slots["food"].value
        food_second = slots["food_second"].value
        purchase_date = slots["purchase_date"].value
        expire_date = slots["expire_date"].value
        
        #delete this
        # date = '2020-5-10'
        
        now = datetime.datetime.now()
        current_time = now.strftime("%Y-%m-%d")
        
        added = {"food_first" : {"not_exist" : True, "DB_found" : False}, "food_second" : {"not_exist" : True, "DB_found" : False}}
        
        if (purchase_date == None and expire_date == None) or (not purchase_date == None):
            DB_result = DBStorage.get_exp_date_str(current_time, food_first)
            
            if DB_result["type"] == "sys":
                added["food_first"]["not_exist"] = pantry.add_food(food_first, DB_result["val"], 'no')
                added["food_first"]["DB_found"] = True
            
        else:
            added["food_first"]["not_exist"] = pantry.add_food(food_first, expire_date, 'no')

        if not food_second == None:
            
            if (purchase_date == None and expire_date == None) or (not purchase_date == None):
                DB_result = DBStorage.get_exp_date_str(current_time, food_second)
                
                if DB_result["type"] == "sys":
                    added["food_second"]["not_exist"] = pantry.add_food(food_second, DB_result["val"], 'no')
                    added["food_second"]["DB_found"] = True
            else:
                added["food_second"]["not_exist"] = pantry.add_food(food_second, expire_date, 'no')
                
        # test_output = str(added)
        
        if food_second == None:
            if added["food_first"]["not_exist"]:
                if added["food_first"]["DB_found"]:
                    speak_output = food_first + " added to my pantry. "
                else:
                    speak_output = food_first + " does not exist in our database, please help us by simply saying something like " + food_first + " expires in 2 days. "
                    ##
                    session_attr = handler_input.attributes_manager.session_attributes
                    session_attr["food_a"] = food_first
                    session_attr["food_b"] = ""
            else:
                speak_output = food_first + " already exist in the pantry, i already updated the expire date. "
                
        else:
            if added["food_first"]["not_exist"] and added["food_second"]["not_exist"]:
                if added["food_first"]["DB_found"] and added["food_second"]["DB_found"]:
                    speak_output = food_first + " and " + food_second + " added to my pantry."
                elif added["food_first"]["DB_found"] and not added["food_second"]["DB_found"]:
                    speak_output = food_first + " added to my pantry," + food_second + " does not exist in our database, please help us by simply saying something like "+food_second+" expires in 2 days. "
                    ##
                    session_attr = handler_input.attributes_manager.session_attributes
                    session_attr["food_b"] = food_second
                    session_attr["food_a"] = ""
                    
                elif not added["food_first"]["DB_found"] and added["food_second"]["DB_found"]:
                    speak_output = food_second + " added to my pantry," + food_first + " does not exist in our database, please help us by simply saying something like "+food_first+" expires in 2 days. "
                    ##
                    session_attr = handler_input.attributes_manager.session_attributes
                    session_attr["food_a"] = food_first
                    session_attr["food_b"] = ""
                else:
                    speak_output = food_first + " and " + food_second + " does not exist in our database, please help us by say something like "+food_second+" expires in 2 days and banana expires in 3 days. "
                    ##
                    session_attr = handler_input.attributes_manager.session_attributes
                    session_attr["food_a"] = food_first
                    session_attr["food_b"] = food_second
                    
            elif (not added["food_first"]["not_exist"]) and added["food_second"]["not_exist"]:
                speak_output = food_first + " already exist in my pantry, i will update the expiring date for you. "
                if added["food_second"]["DB_found"]:
                    speak_output = speak_output + food_second + " added to my pantry. "
                else:
                    speak_output = speak_output + food_second + " does not exist in our database, please help us by simply saying something like "+food_second+" expires in 2 days. "
                    ##
                    session_attr = handler_input.attributes_manager.session_attributes
                    session_attr["food_b"] = food_second
                    session_attr["food_a"] = ""

            elif added["food_first"]["not_exist"] and (not added["food_second"]["not_exist"]):
                speak_output = food_second + " already exist in my pantry, i will update the expiring date for you. "
                if added["food_first"]["DB_found"]:
                    speak_output = speak_output + food_first + " added to my pantry. "
                else:
                    speak_output = speak_output + food_first + " does not exist in our database, please help us by simply saying something like "+food_first+" expires in 2 days. "
                    ##
                    session_attr = handler_input.attributes_manager.session_attributes
                    session_attr["food_a"] = food_first
                    session_attr["food_b"] = ""
            else:
                speak_output = food_first + " and " + food_second + " all already exist in my pantry, i will update their expiring dates for you. "
                    
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

################################## I want to delete what's in my pantry ################################## 

class RemoveIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("DeleteIntent")(handler_input)
    
    def handle(self, handler_input):
        speak_output = "I removed "
        
        # type: (HandlerInput) -> Response
        pantry = Storage(handler_input.attributes_manager)
        slots = handler_input.request_envelope.request.intent.slots
        del_list = []
        del_list.append(slots["food"].value)
        if (not slots["food_second"].value == None):
            del_list.append(slots["food_second"].value)
        for val in del_list:
            if (pantry.delete_food(val)):
                del_list.remove(val)
                speak_output = speak_output + val + " "
        if (len(del_list) > 0):
            speak_output += ". But you actually don't have "
        for val in del_list:
            speak_output = speak_output + val + " "

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )
        
        
def parse_string(duration):
    if not ((duration[-1] == 'D' or duration[-1] == 'W') and duration[0] == 'P'):
        return -1

    for i in range(1, len(duration)-1):
        if not str(duration[i]).isdecimal():
            return -1

    if duration[-1] == 'D':
        return int(duration[1:len(duration)-1])
    else:
        return int(duration[1:len(duration)-1])*7
        
class AddToUserDBIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        ok = ("food_a" in session_attr.keys()) and (not session_attr["food_a"] == "")
        return ok and ask_utils.is_intent_name("AddToUserDBIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = "Thank you! "
        session_attr = handler_input.attributes_manager.session_attributes
        slots = handler_input.request_envelope.request.intent.slots
        food_list = []
        day_list = []
        food_list.append(slots["food_a"].value)
        day_list.append(slots["days_a"].value)
        if (("food_b" in session_attr.keys()) and (not session_attr["food_b"] == "")):
            food_list.append(slots["food_b"].value)
            day_list.append(slots["days_b"].value)
        s = Storage(handler_input.attributes_manager)

        for i in range(0, len(food_list)):
            val = food_list[i]
            day = day_list[i]
            duration = parse_string(day)
            if (duration < 0):
                break
            exp_date = (datetime.datetime.now() + datetime.timedelta(days=duration)).strftime("%Y-%m-%d")
            if (val == session_attr["food_a"]) or (val == session_attr["food_b"]):
                s.delete_food(val)
                s.add_food(val, exp_date, "no")
                DBStorage.set_duration_dur(duration, val)
                speak_output += "Your " + val + " will expire on " + exp_date + ". "
            else:
                DBStorage.set_duration_dur(duration, val)
                
        if (speak_output == "Thank you!"):
            speak_output = "Thank you! Your input makes me smarter!"
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

################################## I want to ask food preservation ################################## 
class AskIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AskIntent")(handler_input)
        
    def handle(self, handler_input):
        pantry = Storage(handler_input.attributes_manager)
        slots = handler_input.request_envelope.request.intent.slots

        food = slots["food"].value
        
        if (pantry.get_exp_date(food) == ""):
            speak_output = food + " does not exist in your pantry. "
        else:
            now_time_obj = datetime.datetime.strptime(pantry.get_exp_date(food), '%Y-%m-%d')
            day_diff =  (now_time_obj - datetime.datetime.now()).days
            speak_output = food + " expires in " + str(day_diff) + " days. "

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )
        
class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = """Welcome to your pantry, where you could manage all your food and view what is expiring. 
            To add or remove up to three items in a sentence, say something like I bought apples yesterday or I cooked the steak. 
            Say what's in my pantry to see what is expiring."""

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(" ")
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = CustomSkillBuilder(persistence_adapter=s3_adapter)

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(AddIntentHandler())
sb.add_request_handler(ViewIntentHandler())
sb.add_request_handler(RemoveIntentHandler())
sb.add_request_handler(AddToUserDBIntentHandler())
sb.add_request_handler(AskIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
