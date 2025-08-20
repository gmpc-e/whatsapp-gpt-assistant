class TwilioMessenger:
    def __init__(self, twilio_client, from_number: str, to_number: str):
        self.client = twilio_client
        self.from_number = from_number
        self.to_number = to_number

    def send(self, text: str):
        self.client.messages.create(
            body=text,
            from_=self.from_number,
            to=self.to_number
        )
