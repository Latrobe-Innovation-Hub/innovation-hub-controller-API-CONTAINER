#!/bin/sh

# innovation-hub-api-container - container1 - password_script.sh
# written by: Andrew McDonald
# initial: 23/05/23
# current: 23/05/23
# version: 0.9

## ===================================================
## script creates an encrypted user access file for
## use with nginx basic-auth.
##
## requires: htpasswd
##
## to use:
##   create a text file with a user:password text pair
##   per user, per line.   Then call script with text
##   file as argument.
##     eg: ./password_script user_credentials.txt
##
## eg txt file layout for creating 3 users:
##
##   user_credentials.txt:
##   user1:password1
##   user2:password2
##   user3:password3
## ===================================================

# create access file if it deosn't exist
touch /etc/nginx/auth/.htpasswd

# set password:username delimter, :
FS=":"

FILE=$1

while read line || [ -n "$line" ];
do
        # store field 1
        NAME=$(echo $line|cut -d$FS -f1)

        # store field 2
        PASSWORD=$(echo $line|cut -d$FS -f2)

        # add username and encrypted password to access file
        htpasswd -b /etc/nginx/auth/.htpasswd $NAME $PASSWORD >/dev/null 2>&1
done < $FILE

exit
