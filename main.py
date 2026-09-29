import subprocess

if __name__ == '__main__':
    subprocess.run('python manage.py migrate', shell=True)
    subprocess.run('python manage.py runserver 0.0.0.0:8000', shell=True)

