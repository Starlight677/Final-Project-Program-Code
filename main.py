import subprocess

if __name__ == '__main__':
    subprocess.run('python manage.py migrate', shell=True)
    subprocess.run('python manage.py runserver', shell=True)

