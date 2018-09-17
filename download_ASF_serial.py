#!/usr/bin/python

# Usage:
#
#    In a terminal/command line, cd to the directory where this file lives. Then...
#
#    With embedded urls: ( download the hardcoded list of files in the 'files =' block below)
#
#       python ./download-all-2018-08-04_10-54-13.py
#
#    Download all files in a Metalink/CSV: (downloaded from ASF Vertex)
#
#       python ./download-all-2018-08-04_10-54-13.py /path/to/downloads.metalink localmetalink.metalink localcsv.csv
#
#    Compatibility: python >= 2.6.5, 2.7.5, 3.0
#
#    If downloading from a trusted source with invalid SSL Certs, use --insecure to ignore
#
#    For more information on bulk downloads, navigate to:
#        https://www.asf.alaska.edu/data-tools/bulk-download/
#
#
#
#    This script was generated by the Alaska Satellite Facility's bulk download service.
#    For more information on the service, navigate to:
#        http://bulk-download.asf.alaska.edu/help
#

import sys, csv
import os, os.path
import tempfile, shutil
import re

import base64
import time
import getpass
import ssl

import xml.etree.ElementTree as ET

#############
# This next block is a bunch of Python 2/3 compatability

try:
   # Python 2.x Libs
   from urllib2 import build_opener, install_opener, Request, urlopen, HTTPError
   from urllib2 import URLError, HTTPSHandler,  HTTPHandler, HTTPCookieProcessor

   from cookielib import MozillaCookieJar
   from StringIO import StringIO

except ImportError as e:

   # Python 3.x Libs
   from urllib.request import build_opener, install_opener, Request, urlopen
   from urllib.request import HTTPHandler, HTTPSHandler, HTTPCookieProcessor
   from urllib.error import HTTPError, URLError

   from http.cookiejar import MozillaCookieJar
   from io import StringIO

class bulk_downloader:
    def __init__(self):
        # List of files to download
        self.files = [ "https://datapool.asf.alaska.edu/SLC/SB/S1B_IW_SLC__1SDV_20180707T114940_20180707T115004_011704_01587A_AA26.zip",
                       "https://datapool.asf.alaska.edu/SLC/SB/S1B_IW_SLC__1SDV_20180707T114912_20180707T114942_011704_01587A_4B42.zip",
                       "https://datapool.asf.alaska.edu/SLC/SA/S1A_IW_SLC__1SDV_20170629T215253_20170629T215322_017254_01CCAD_8B5A.zip",
                       "https://datapool.asf.alaska.edu/SLC/SA/S1A_IW_SLC__1SDV_20170605T215251_20170605T215320_016904_01C204_B139.zip",
                       "https://datapool.asf.alaska.edu/SLC/SA/S1A_IW_SLC__1SDV_20170524T215250_20170524T215319_016729_01BC8E_E6AD.zip",
                       "https://datapool.asf.alaska.edu/SLC/SA/S1A_IW_SLC__1SDV_20170512T215250_20170512T215319_016554_01B72B_A208.zip",
                       "https://datapool.asf.alaska.edu/SLC/SA/S1A_IW_SLC__1SDV_20170430T215249_20170430T215318_016379_01B1DF_F670.zip",
                       "https://datapool.asf.alaska.edu/SLC/SA/S1A_IW_SLC__1SDV_20170418T215249_20170418T215318_016204_01AC92_F2B1.zip",
                       "https://datapool.asf.alaska.edu/SLC/SA/S1A_IW_SLC__1SDV_20170406T215248_20170406T215317_016029_01A730_08DA.zip",
                       "https://datapool.asf.alaska.edu/SLC/SA/S1A_IW_SLC__1SDV_20170325T215248_20170325T215317_015854_01A1FC_6DB3.zip",
                       "https://datapool.asf.alaska.edu/SLC/SA/S1A_IW_SLC__1SDV_20170313T215247_20170313T215316_015679_019CCC_6A05.zip" ]

        # Local stash of cookies so we don't always have to ask
        self.cookie_jar_path = os.path.join( os.path.expanduser('~'), ".bulk_download_cookiejar.txt")
        self.cookie_jar = None

        self.asf_urs4 = { 'url': 'https://urs.earthdata.nasa.gov/oauth/authorize',
                 'client': 'BO_n7nTIlMljdvU6kRRB3g',
                 'redir': 'https://vertex.daac.asf.alaska.edu/services/urs4_token_request'}
                 
        # Make sure we can write it our current directory
        if os.access(os.getcwd(), os.W_OK) is False:
            print ("WARNING: Cannot write to current path! Check permissions for {0}".format(os.getcwd()))
            exit(-1)

        # For SSL
        self.context = {}

        # Check if user handed in a Metalink or CSV:
        if len(sys.argv) > 0:
            download_files = []
            input_files = []
            for arg in sys.argv[1:]:
                if arg == '--insecure':
                    try:
                        ctx = ssl.create_default_context()
                        ctx.check_hostname = False
                        ctx.verify_mode = ssl.CERT_NONE
                        self.context['context'] = ctx
                    except AttributeError:
                        # Python 2.6 won't complain about SSL Validation
                        pass
                 
                elif arg.endswith('.metalink') or arg.endswith('.csv'):
                    if os.path.isfile(arg):
                        input_files.append( arg )
                        if arg.endswith('.metalink'):
                            new_files = self.process_metalink(arg)
                        else:
                            new_files = self.process_csv(arg)
                        
                        #print(new_files)
                        if new_files is not None:
                            for file_url in (new_files):
                                download_files.append( file_url )
                    else:
                         print (" > I cannot find the input file you specified: {0}".format(arg))
                else:
                    print (" > Command line argument '{0}' makes no sense, ignoring.".format(arg))

            if len(input_files) > 0:
                if len(download_files) > 0:
                    print (" > Processing {0} downloads from {1} input files. ".format(len(download_files), len(input_files)))
                    self.files = download_files
                else:
                    print (" > I see you asked me to download files from {0} input files, but they had no downloads!".format(len(input_files)))
                    print (" > I'm super confused and exiting.")
                    exit(-1)
              
        # Make sure cookie_jar is good to go!
        self.get_cookie()

         # summary
        self.total_bytes = 0
        self.total_time = 0
        self.cnt = 0
        self.success = []
        self.failed = []
        self.skipped = []


    # Get and validate a cookie
    def get_cookie(self):
       if os.path.isfile(self.cookie_jar_path):
          self.cookie_jar = MozillaCookieJar()
          self.cookie_jar.load(self.cookie_jar_path)

          # make sure cookie is still valid
          if self.check_cookie():
             print(" > Re-using previous cookie jar.")
             return True
          else:
             print(" > Could not validate old cookie Jar")

       # We don't have a valid cookie, prompt user or creds
       print ("No existing URS cookie found, please enter Earthdata username & password:")
       print ("(Credentials will not be stored, saved or logged anywhere)")

       # Keep trying 'till user gets the right U:P
       while self.check_cookie() is False:
          self.get_new_cookie()

       return True

    # Validate cookie before we begin
    def check_cookie(self):

       if self.cookie_jar is None:
          print (" > Cookiejar is bunk: {0}".format(self.cookie_jar))
          return False

       # File we know is valid, used to validate cookie
       file_check = 'https://urs.earthdata.nasa.gov/profile'

       # Apply custom Redirect Hanlder
       opener = build_opener(HTTPCookieProcessor(self.cookie_jar), HTTPHandler(), HTTPSHandler(**self.context))
       install_opener(opener)

       # Attempt a HEAD request
       request = Request(file_check)
       request.get_method = lambda : 'HEAD'
       try:
          print (" > attempting to download {0}".format(file_check))
          response = urlopen(request)
          resp_code = response.getcode()
          # Make sure we're logged in
          if not self.check_cookie_is_logged_in(self.cookie_jar):
             return False

          # Save cookiejar
          self.cookie_jar.save(self.cookie_jar_path)

       except HTTPError:
          # If we ge this error, again, it likely means the user has not agreed to current EULA
          print ("\nIMPORTANT: ")
          print ("Your user appears to lack permissions to download data from the ASF Datapool.")
          print ("\n\nNew users: you must first log into Vertex and accept the EULA. In addition, your Study Area must be set at Earthdata https://urs.earthdata.nasa.gov")
          exit(-1)

       # This return codes indicate the USER has not been approved to download the data
       if resp_code in (300, 301, 302, 303):
          try:
             redir_url = response.info().getheader('Location')
          except AttributeError:
             redir_url = response.getheader('Location')

          #Funky Test env:
          if ("vertex.daac.asf.alaska.edu" in redir_url and "test" in self.asf_urs4['redir']):
             print ("Cough, cough. It's dusty in this test env!")
             return True

          print ("Redirect ({0}) occured, invalid cookie value!".format(resp_code))
          return False

       # These are successes!
       if resp_code in (200, 307):
          return True

       return False

    def get_new_cookie(self):
       # Start by prompting user to input their credentials

       # Another Python2/3 workaround
       try:
          #new_username = raw_input("Username: ")
          new_username = sys.argv[2]
       except NameError:
          #new_username = input("Username: ")
          new_username = sys.argv[2]
       #new_password = getpass.getpass(prompt="Password (will not be displayed): ")
       new_password = sys.argv[4]

       # Build URS4 Cookie request
       auth_cookie_url = self.asf_urs4['url'] + '?client_id=' + self.asf_urs4['client'] + '&redirect_uri=' + self.asf_urs4['redir'] + '&response_type=code&state='

       try:
          #python2
          user_pass = base64.b64encode (bytes(new_username+":"+new_password))
       except TypeError:
          #python3
          user_pass = base64.b64encode (bytes(new_username+":"+new_password, "utf-8"))
          user_pass = user_pass.decode("utf-8")

       # Authenticate against URS, grab all the cookies
       self.cookie_jar = MozillaCookieJar()
       opener = build_opener(HTTPCookieProcessor(self.cookie_jar), HTTPHandler(), HTTPSHandler(**self.context))
       request = Request(auth_cookie_url, headers={"Authorization": "Basic {0}".format(user_pass)})

       # Watch out cookie rejection!
       try:
          response = opener.open(request)
       except HTTPError as e:
          if e.code == 401:
             print (" > Username and Password combo was not successful. Please try again.")
             return False
          else:
             # If an error happens here, the user most likely has not confirmed EULA.
             print ("\nIMPORTANT: There was an error obtaining a download cookie!")
             print ("Your user appears to lack permission to download data from the ASF Datapool.")
             print ("\n\nNew users: you must first log into Vertex and accept the EULA. In addition, your Study Area must be set at Earthdata https://urs.earthdata.nasa.gov")
             exit(-1)
       except URLError as e:
          print ("\nIMPORTANT: There was a problem communicating with URS, unable to obtain cookie. ")
          print ("Try cookie generation later.")
          exit(-1)

       # Did we get a cookie?
       if self.check_cookie_is_logged_in(self.cookie_jar):
          #COOKIE SUCCESS!
          self.cookie_jar.save(self.cookie_jar_path)
          return True

       # if we aren't successful generating the cookie, nothing will work. Stop here!
       print ("WARNING: Could not generate new cookie! Cannot proceed. Please try Username and Password again.")
       print ("Response was {0}.".format(response.getcode()))
       print ("\n\nNew users: you must first log into Vertex and accept the EULA. In addition, your Study Area must be set at Earthdata https://urs.earthdata.nasa.gov")
       exit(-1)

    # make sure we're logged into URS
    def check_cookie_is_logged_in(self, cj):
       for cookie in cj:
          if cookie.name == 'urs_user_already_logged':
              # Only get this cookie if we logged in successfully!
              return True
       
       return False


    # Download the file
    def download_file_with_cookiejar(self, url, file_count, total, recursion=False):
       # see if we've already download this file and if it is that it is the correct size
       print("URL: "+url)
       print(os.path.basename(url))
       download_file = os.path.basename(url).split('?')[0]
       if os.path.isfile(download_file):
          try:
             request = Request(url)
             request.get_method = lambda : 'HEAD'
             response = urlopen(request)
             remote_size = self.get_total_size(response)
             # Check that we were able to derive a size.
             if remote_size:
                 local_size = os.path.getsize(download_file)
                 if remote_size < (local_size+(local_size*.01)) and remote_size > (local_size-(local_size*.01)):
                     print (" > Download file {0} exists! \n > Skipping download of {1}. ".format(download_file, url))
                     return None,None
                 #partial file size wasn't full file size, lets blow away the chunk and start again
                 print (" > Found {0} but it wasn't fully downloaded. Removing file and downloading again.".format(download_file))
                 os.remove(download_file)

          except ssl.CertificateError as e:
             print (" > ERROR: {0}".format(e))
             print (" > Could not validate SSL Cert. You may be able to overcome this using the --insecure flag")
             return False,None

          except HTTPError as e:
             if e.code == 401:
                 print (" > IMPORTANT: Your user may not have permission to download this type of data!")
             else:
                 print (" > Unknown Error, Could not get file HEAD: {0}".format(e))

          except URLError as e:
             print ("URL Error (from HEAD): {0}, {1}".format( e.reason, url))
             if "ssl.c" in "{0}".format(e.reason):
                 print ("IMPORTANT: Remote location may not be accepting your SSL configuration. This is a terminal error.")
             return False,None

       # attempt https connection
       try:
          request = Request(url)
          response = urlopen(request)

          # Watch for redirect
          if response.geturl() != url:
       
             # See if we were redirect BACK to URS for re-auth. 
             if 'https://urs.earthdata.nasa.gov/oauth/authorize' in response.geturl():

                 if recursion:
                     print (" > Entering seemingly endless auth loop. Aborting. ")
                     return False, None
     
                 # make this easier. If there is no app_type=401, add it
                 new_auth_url = response.geturl()
                 if "app_type" not in new_auth_url:
                     new_auth_url += "&app_type=401"

                 print (" > While attempting to download {0}....".format(url))
                 print (" > Need to obtain new cookie from {0}".format(new_auth_url))
                 old_cookies = [cookie.name for cookie in self.cookie_jar]
                 opener = build_opener(HTTPCookieProcessor(self.cookie_jar), HTTPHandler(), HTTPSHandler(**self.context))
                 request = Request(new_auth_url)
                 try:
                     response = opener.open(request)
                     for cookie in self.cookie_jar:
                         if cookie.name not in old_cookies:
                              print (" > Saved new cookie: {0}".format(cookie.name))
                          
                              # A little hack to save session cookies
                              if cookie.discard:
                                   cookie.expires = int(time.time()) + 60*60*24*30
                                   print (" > Saving session Cookie that should have been discarded! ")
             
                     self.cookie_jar.save(self.cookie_jar_path, ignore_discard=True, ignore_expires=True)
                 except HTTPError as e:
                     print ("HTTP Error: {0}, {1}".format( e.code, url))
                     return False,None

                 # Okay, now we have more cookies! Lets try again, recursively!
                 print (" > Attempting download again with new cookies!")
                 return self.download_file_with_cookiejar(url, file_count, total, recursion=True)       

             print (" > 'Temporary' Redirect download @ Remote archive:\n > {0}".format(response.geturl()))

          # seems to be working
          print ("({0}/{1}) Downloading {2}".format(file_count, total, url))

          # Open our local file for writing and build status bar
          tf = tempfile.NamedTemporaryFile(mode='w+b', delete=False, dir='.')
          self.chunk_read(response, tf, report_hook=self.chunk_report)
          
          # Reset download status
          sys.stdout.write('\n')

          tempfile_name = tf.name
          tf.close()

       #handle errors
       except HTTPError as e:
          print ("HTTP Error: {0}, {1}".format( e.code, url))

          if e.code == 401:
             # Check for a human readable 401
             with open(tempfile_name, 'r') as myfile:
                 redir_html = myfile.read()
             redirect_url = self.get_redirect_url_from_error(redir_html)
             if redirect_url:
                 print("Found: {0}".format(redirect_url.group(0)))
                 exit(0)
             print (" > IMPORTANT: Your user does not have permission to download this type of data!")
     
          if e.code == 403:
             print (" > Got a 403 Error trying to download this file.  ")
             print (" > You MAY need to log in this app and agree to a EULA. ")

          return False,None

       except URLError as e:
          print ("URL Error (from GET): {0}, {1}, {2}".format(e, e.reason, url))
          if "ssl.c" in "{0}".format(e.reason):
              print ("IMPORTANT: Remote location may not be accepting your SSL configuration. This is a terminal error.")
          return False,None

       except ssl.CertificateError as e:
          print (" > ERROR: {0}".format(e))
          print (" > Could not validate SSL Cert. You may be able to overcome this using the --insecure flag")
          return False,None

       # Return the file size
       shutil.copy(tempfile_name, download_file)
       os.remove(tempfile_name)
       file_size = self.get_total_size(response)
       actual_size = os.path.getsize(download_file)
       if file_size is None:
           # We were unable to calculate file size.
           file_size = actual_size
       return actual_size,file_size

    def get_redirect_url_from_error(self, error):
       find_redirect = re.compile(r"id=\"redir_link\"\s+href=\"(\S+)\"")
       print ("error file was: {}".format(error))
       redirect_url = find_redirect.search(error)
       if redirect_url:
          print("Found: {0}".format(redirect_url.group(0)))
          return (redirect_url.group(0))
     
       return None
       

    #  chunk_report taken from http://stackoverflow.com/questions/2028517/python-urllib2-progress-hook
    def chunk_report(self, bytes_so_far, file_size):
       if file_size is not None:
           percent = float(bytes_so_far) / file_size
           percent = round(percent*100, 2)
           sys.stdout.write(" > Downloaded %d of %d bytes (%0.2f%%)\r" %
               (bytes_so_far, file_size, percent))
       else:
           # We couldn't figure out the size.
           sys.stdout.write(" > Downloaded %d of unknown Size\r" % (bytes_so_far))

    #  chunk_read modified from http://stackoverflow.com/questions/2028517/python-urllib2-progress-hook
    def chunk_read(self, response, local_file, chunk_size=8192, report_hook=None):
       file_size = self.get_total_size(response)
       bytes_so_far = 0

       while 1:
          chunk = response.read(chunk_size)
          try:
             local_file.write(chunk)
          except TypeError:
             local_file.write(chunk.decode(local_file.encoding))
          bytes_so_far += len(chunk)

          if not chunk:
             break

          if report_hook:
             report_hook(bytes_so_far, file_size)

       return bytes_so_far

    def get_total_size(self, response):
       try:
          file_size = response.info().getheader('Content-Length').strip()
       except AttributeError:
          try: 
             file_size = response.getheader('Content-Length').strip()
          except AttributeError:
             print ("> Problem getting size")
             return None
       
       return int(file_size)


    # Get download urls from a metalink file
    def process_metalink(self, ml_file):
       print ("Processing metalink file: {0}".format(ml_file))
       with open(ml_file, 'r') as ml:
          xml = ml.read()

       # Hack to remove annoying namespace
       it = ET.iterparse(StringIO(xml))
       for _, el in it:
          if '}' in el.tag:
             el.tag = el.tag.split('}', 1)[1]  # strip all namespaces
       root = it.root

       dl_urls = []
       ml_files = root.find('files')
       for dl in ml_files:
          dl_urls.append(dl.find('resources').find('url').text)

       if len(dl_urls) > 0:
          return dl_urls
       else:
          return None

    # Get download urls from a csv file
    def process_csv(self, csv_file):
       print ("Processing csv file: {0}".format(csv_file))

       dl_urls = []
       with open(csv_file, 'r') as csvf:
          try:
             csvr = csv.reader(csvf, delimiter=',')
             for row in csvr:
                dl_urls.append(row)
          except csv.Error as e:
             print ("WARNING: Could not parse file %s, line %d: %s. Skipping." % (csv_file, csvr.line_num, e))
             return None
          except KeyError as e:
             print ("WARNING: Could not find URL column in file %s. Skipping." % (csv_file))
       
       if len(dl_urls) > 0:
          return dl_urls
       else:
          return None
    
    # Download all the files in the list
    def download_files(self):
        self.files = self.files[0]
        for file_name in self.files:

            # download counter
            self.cnt += 1

            # set a timer
            start = time.time()

            # run download
            size,total_size = self.download_file_with_cookiejar(file_name, self.cnt, len(self.files))

            # calculte rate
            end = time.time()

            # stats:
            if size is None:
                self.skipped.append(file_name)
            # Check to see that the download didn't error and is the correct size
            elif size is not False and (total_size < (size+(size*.01)) and total_size > (size-(size*.01))):
                # Download was good!
                elapsed = end - start
                elapsed = 1.0 if elapsed < 1 else elapsed
                rate = (size/1024**2)/elapsed

                print ("Downloaded {0}b in {1:.2f}secs, Average Rate: {2:.2f}MB/sec".format(size, elapsed, rate))

                # add up metrics
                self.total_bytes += size
                self.total_time += elapsed
                self.success.append( {'file':file_name, 'size':size } )

            else:
                print ("There was a problem downloading {0}".format(file_name))
                self.failed.append(file_name)

    def print_summary(self):
        # Print summary:
        print ("\n\nDownload Summary ")
        print ("--------------------------------------------------------------------------------")
        print ("  Successes: {0} files, {1} bytes ".format(len(self.success), self.total_bytes))
        for success_file in self.success:
           print ("           - {0}  {1:.2f}MB".format(success_file['file'],(success_file['size']/1024.0**2)))
        if len(self.failed) > 0:
           print ("  Failures: {0} files".format(len(self.failed)))
           for failed_file in self.failed:
              print ("          - {0}".format(failed_file))
        if len(self.skipped) > 0:
           print ("  Skipped: {0} files".format(len(self.skipped)))
           for skipped_file in self.skipped:
              print ("          - {0}".format(skipped_file))
        if len(self.success) > 0:
           print ("  Average Rate: {0:.2f}MB/sec".format( (self.total_bytes/1024.0**2)/self.total_time))
        print ("--------------------------------------------------------------------------------")
        

if __name__ == "__main__":
    downloader = bulk_downloader()
    downloader.download_files()
    downloader.print_summary()
