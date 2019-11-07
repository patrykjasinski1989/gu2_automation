## gu2_automation

A Python script that automates the resolution of repetitive 2nd support line tickets for VC3 BSS project.

#### Installing

Change the values of *username* and *password* in the *install.sh* script to your github credentials.

Run the *install.sh* script on any Ubuntu 18.04 or 16.04 machine, preferably on VM.

You can also use Dockerfile to build an image (keep the *config.py* file with your access data in the same directory):
```
docker build . -t *YOUR_TAG*
```

#### Running

Fill your access data in the *config.py* file.

To run the script, simply execute the following:
```
python gu2_sales_robot.py
```

To run the docker container:
```
docker run *YOUR_TAG*
```

#### Other functionalities

```
python gu2_int_robot.py
python pbi_report.py
python resolution_stats.py
```
