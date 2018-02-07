import os

class CustomerNameMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        '''
        Set the "cust_name" parameter in the request if empty.
        Take its value from the current session (in fact, this is priority)
        '''
        #print(request.session)
        if 'customer' in request.session:
            #print(request.session['customer'])
            #request_path = os.path.join(request.path, request.session['customer'])
            #print("Request Path (middleware):", request.path)
            pass # unuseful

        response = self.get_response(request)
        return response
