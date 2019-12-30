import os

path = os.path

application_path = path.realpath(__file__)
db_path = path.realpath(application_path + 'data/db')
saves_path = path.realpath(application_path + 'data/saves')

