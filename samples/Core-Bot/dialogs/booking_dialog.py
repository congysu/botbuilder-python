from botbuilder.dialogs import WaterfallDialog, WaterfallStepContext, DialogTurnResult
from botbuilder.dialogs.prompts import ConfirmPrompt, TextPrompt, PromptOptions
from botbuilder.core import MessageFactory
from .cancel_and_help_dialog import CancelAndHelpDialog
from .date_resolver_dialog import DateResolverDialog

class BookingDialog(CancelAndHelpDialog):

    def __init__(self, dialog_id: str = None):
        super(BookingDialog, self).__init__(dialog_id or BookingDialog.__name__)

        self.add_dialog(TextPrompt(TextPrompt.__name__))
        self.add_dialog(ConfirmPrompt(ConfirmPrompt.__name__))
        self.add_dialog(DateResolverDialog(DateResolverDialog.__name__))
        self.add_dialog(WaterfallDialog(WaterfallDialog.__name__, [

        ]))

        self.initial_dialog_id(WaterfallDialog.__name__)
    
    """
    If a destination city has not been provided, prompt for one.
    """
    async def destination_step(self, step_context: WaterfallStepContext) -> DialogTurnResult: 
        booking_details = step_context.options

        if (booking_details.destination is None): 
            return await step_context.prompt(TextPrompt.__name__, PromptOptions(prompt= MessageFactory.text('To what city would you like to travel?')))
        else: 
            return await step_context.next(booking_details.destination)

    """
    If an origin city has not been provided, prompt for one.
    """
    async def origin_step(self, step_context: WaterfallStepContext) -> DialogTurnResult: 
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.destination = step_context.result
        if (booking_details.origin is None): 
            return await step_context.prompt(TextPrompt.__name__, PromptOptions(prompt= MessageFactory.text('From what city will you be travelling?')))
        else: 
            return await step_context.next(booking_details.origin)

    """
    If a travel date has not been provided, prompt for one.
    This will use the DATE_RESOLVER_DIALOG.
    """
    async def travel_date_step(self, step_context: WaterfallStepContext) -> DialogTurnResult: 
        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.origin = step_context.result
        if (not booking_details.travel_date or self.is_ambiguous(booking_details.travelDate)): 
            return await step_context.begin_dialog(DateResolverDialog.__name__, date= booking_details.travel_date)
        else: 
            return await step_context.next(booking_details.travelDate)

    """
    Confirm the information the user has provided.
    """
    async def confirm_step(self, step_context: WaterfallStepContext) -> DialogTurnResult: 
        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.travel_date= step_context.result
        msg = f'Please confirm, I have you traveling to: { booking_details.destination } from: { booking_details.origin } on: { booking_details.travel_date}.'

        # Offer a YES/NO prompt.
        return await step_context.prompt(ConfirmPrompt.__name__, PromptOptions(prompt= MessageFactory.text(msg)))

    """
    Complete the interaction and end the dialog.
    """
    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult: 
        if step_context.result: 
            booking_details = step_context.options

            return await step_context.end_dialog(booking_details)
        else: 
            return await step_context.end_dialog()

    def is_ambiguous(self, timex: str) -> bool: 
        timex_property = TimexProperty(timex)
        return 'definite' not in timex_property.types


    
    