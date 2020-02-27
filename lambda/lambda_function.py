# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import ask_sdk_core.utils as ask_utils
import os
from ask_sdk_s3.adapter import S3Adapter
s3_adapter = S3Adapter(bucket_name=os.environ["S3_PERSISTENCE_BUCKET"])

from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

# Custom imports
import requests
from twython import Twython
from requests_oauthlib import OAuth1
import re
import json
import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)
        
    
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Hello, ask me, What are the top five trends?"
        reprompt = "Social trending here... ask me, What are the top five trends"

        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(reprompt)
                .response
        )

class CaptureNumberOfTrendsIntentHandler(AbstractRequestHandler):
    """Handler for Capture number of trends Intent."""
    
    DATE_STR_FORMAT = "%d/%m/%yT%H:%M:%S"
    DATA_REFRESH_RATE = 300
    
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("CaptureNumberOfTrendsIntent")(handler_input)
        
    # Helper method
    def add_spaces(self, aWord):
        """
        For trending hashtags missing spaces, a space is added back to the word.
        It only works if capital letters has been used to define the start of 
        each new word, so 'ValentinesDay' becomes 'Valentines Day'
        """
        
        index = 0
        
        for char in aWord:
            if index != 0:
                if (aWord[index].isupper() and aWord[index-1].islower()) or (aWord[index].isdigit() and not aWord[index-1].isdigit()):
                    aWord = aWord[:index] + " " + aWord[index:]
                    index += 1
            index += 1
            
        return aWord
        
    def get_top_trends(self, how_many_trends, trends):
        """
        Some comments
        """
        
        top_trends = []
        temp = trends.copy()

        for trend in temp:
            if trend["tweet_volume"] == None:
                trend["tweet_volume"] = 0
        
        temp.sort(key=lambda x: x["tweet_volume"], reverse=True)

        for trend in temp:
            if len(top_trends) >= how_many_trends:
                break
            else:
                if trend["promoted_content"] == None and not self.cjk_detect(trend["name"]):
                    top_trends.append(trend)

        return top_trends
        
    def time_diff(self, before, after):
        """
        Some comments
        """
        
        assert type(before) == datetime.datetime, "argument 'before' should be of type datetime.datetime"
        assert type(after) == datetime.datetime, "argument 'after' should be of type datetime.datetime"
        
        difference = round((after - before).total_seconds())

        return difference
	
    def cjk_detect(self, texts):
        """
        Some comments
        """
        
        # korean
        if re.search("[\uac00-\ud7a3]", texts):
            return True
        # japanese
        if re.search("[\u3040-\u30ff]", texts):
            return True
        # chinese
        if re.search("[\u4e00-\u9FFF]", texts):
            return True
        return False
        
    def get_woeids(self):
        """
        Some comments
        """
        
        # get cwd
        cwd = os.getcwd()
        file = open(cwd + "/woeids.json", "r")
        data = file.read()
        file.close()
        woeids = json.loads(data)
        
        return woeids
        
    def get_twitter_auth(self):
        """
        Some comments
        """
        
        consumer_key = 'NhGw9k5x4IaoKp8ysBV1LRs7S'
        consumer_secret = 'zknbFSFGnc1mZNbZByusbHXkRfTXZFOrADn73VXiGPgQS0VbPs'
        access_token = '1069016670-Ph6RPyo8yRSSxC6loW5JGriPlgKiCZHgPoEIvES'
        access_token_secret = '4NgeYBpk0jdYfV9YgNUnwDqpLQaVKSiyBpOjk618yHQui'
        return OAuth1(consumer_key, consumer_secret, access_token, access_token_secret)
        
    def get_twitter_trends(self, auth, handler_input):
        """
        Some comments
        """
        
        uk = "23424975" # United Kingdom WOEID
        url = "https://api.twitter.com/1.1/trends/place.json?id={woeid}".format(woeid=uk) 
        res = requests.get(url, auth=auth)
        trends = res.json()[0]['trends']
        
        self.save_trending_data(trends, handler_input)
        
        return trends
        
    def create_text_from_top_trends(self, top_trends):
        """
        Some comments
        """
        
        speak_output = "Your local top trends are... "
        
        # get top user defined number of trends by tweet volume
        for trend in top_trends:
            speak_output += self.add_spaces(trend['name'].replace("#", ""))
            speak_output += ", "
            
        speak_output = speak_output[:-2]
        
        return speak_output
        
    def save_trending_data(self, trends, handler_input):
        """
        Some comments
        """
        
        try:
            attributes_manager = handler_input.attributes_manager
            now = datetime.datetime.now()
            now_str = self.convert_datetime_to_str(now, self.DATE_STR_FORMAT)
            trending_attributes = {
                "last_cached": now_str,
                "trending_data": trends
            }
            attributes_manager.persistent_attributes = trending_attributes
            attributes_manager.save_persistent_attributes()
        except:
            return False
        
        return True
        
    def convert_str_to_datetime(self, date_str, str_format):
        """
        Some comments
        """
        
        return datetime.datetime.strptime(date_str, str_format)
        
    def convert_datetime_to_str(self, datetime_object, datetime_str_format):
        """
        Some comments
        """
        
        return datetime_object.strftime(datetime_str_format)
        
    def get_stored_data(self, handler_input):
        """
        Some comments
        """
        
        return handler_input.attributes_manager.persistent_attributes
    	
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        
        # Get user input
        slots = handler_input.request_envelope.request.intent.slots
        number_of_trends_wanted = int(slots["number"].value)
        
        # Get stored data
        stored_data = self.get_stored_data(handler_input)
        last_cached = self.convert_str_to_datetime(stored_data["last_cached"], self.DATE_STR_FORMAT)
        
        if self.time_diff(last_cached, datetime.datetime.now()) < self.DATA_REFRESH_RATE:
            trends = stored_data["trending_data"]
            top_trends = self.get_top_trends(number_of_trends_wanted, trends)
            speak_output = self.create_text_from_top_trends(top_trends)
        else:
            auth = self.get_twitter_auth()
            trends = self.get_twitter_trends(auth, handler_input)
            top_trends = self.get_top_trends(number_of_trends_wanted, trends)
            speak_output = self.create_text_from_top_trends(top_trends)

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can ask me, what are the top five trends, what are the top ten trends etc"
        ask_output = "Go ahead, ask me for the top five trends"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
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
                .ask(speak_output)
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = CustomSkillBuilder(persistence_adapter=s3_adapter)

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CaptureNumberOfTrendsIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()