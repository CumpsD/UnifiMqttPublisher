#!/usr/bin/env python

from pyunifi.controller import Controller
import time
import paho.mqtt.client as mqtt
import json
import os

#### Env VARS ####
UNIFI_HOST = os.getenv('UNIFI_HOST')
UNIFI_USER = os.getenv('UNIFI_USER')
UNIFI_PASS = os.getenv('UNIFI_PASS')
UNIFI_VERSION = os.getenv('UNIFI_VERSION', 'UDMP-unifiOS')
UNIFI_SITE = os.getenv('UNIFI_SITE', 'default')
UNIFI_PORT = os.getenv('UNIFI_PORT', '443')
VERIFY_SSL = True

MQTT_HOST = os.getenv('MQTT_HOST')
MQTT_USER = os.getenv('MQTT_USER')
MQTT_PASS = os.getenv('MQTT_PASS')

POLL_FREQUENCY = int(os.getenv('POLL_FREQUENCY', 30))

POE_MACS = os.getenv('POE_MACS')

class UnifiMqttPublisher:
    def __init__(self):
        self.mqttClient = mqtt.Client()
        self.mqttClient.username_pw_set(username=MQTT_USER, password=MQTT_PASS)
        self.mqttClient.connect(MQTT_HOST, 1883, 60)

        self.unifiClient = Controller(host=UNIFI_HOST,username=UNIFI_USER,password=UNIFI_PASS,port=UNIFI_PORT,version=UNIFI_VERSION,site_id=UNIFI_SITE,ssl_verify=VERIFY_SSL)

    def run(self):
        while (True):
            print('Publishing..')
            self.publishControllerStats()
            self.publishDeviceStats()
            time.sleep(POLL_FREQUENCY)

    def publishDeviceStats(self):
        devs = POE_MACS.split(";")
        for dev in devs:
            info = self.unifiClient.get_device_stat(dev)
            device_payload = {}
            device_payload['mac'] = dev
            device_payload['model'] = info['model']

            self.mqttClient.publish('unifi/stats/device-' + dev, payload=json.dumps(device_payload))

            for x in range(len(info['port_table'])):
                port_payload = {}
                port_payload['port_number'] = info['port_table'][x]['port_idx']
                port_payload['port_name'] = info['port_table'][x]['name']
                port_payload['port_poe'] = info['port_table'][x]['port_poe']

                port_poe = info['port_table'][x]['port_poe']
                if port_poe == True:
                    port_payload['poe_power'] = round(float(info['port_table'][x]['poe_power']), 2)
                    port_payload['poe_voltage'] = round(float(info['port_table'][x]['poe_voltage']), 2)
                    port_payload['poe_current'] = round(float(info['port_table'][x]['poe_current']), 2)

                self.mqttClient.publish('unifi/stats/device-' + dev + '/' + port_payload['port_number'], payload=json.dumps(port_payload))

    def publishControllerStats(self):
        aps = self.unifiClient.get_aps()
        clients = self.unifiClient.get_clients()
        health = self.unifiClient.get_healthinfo()

        payload = {}
        payload['num_aps'] = len(aps)
        payload['num_clients'] = len(clients)

        wlanHealth = next((x for x in health if x['subsystem'] == 'wlan'), None)
        if (wlanHealth):
            payload['wlan_status'] = wlanHealth['status']
            payload['wlan_clients'] = wlanHealth['num_user']
            payload['wlan_guests'] = wlanHealth['num_guest']
            payload['wlan_ap'] = wlanHealth['num_ap']
            payload['wlan_pending'] = wlanHealth['num_pending']
            payload['wlan_adopted'] = wlanHealth['num_adopted']
            payload['wlan_disabled'] = wlanHealth['num_disabled']
            payload['wlan_disconnected'] = wlanHealth['num_disconnected']
            payload['wlan_iot'] = wlanHealth['num_iot']

        lanHealth = next((x for x in health if x['subsystem'] == 'lan'), None)
        if (lanHealth):
            payload['lan_status'] = lanHealth['status']
            payload['lan_clients'] = lanHealth['num_user']
            payload['lan_guests'] = lanHealth['num_guest']
            payload['lan_adopted'] = lanHealth['num_adopted']
            payload['lan_disconnected'] = lanHealth['num_disconnected']
            payload['lan_pending'] = lanHealth['num_pending']
            payload['lan_iot'] = lanHealth['num_iot']
            payload['lan_sw'] = lanHealth['num_sw']

        #print(payload)
        self.mqttClient.publish('unifi/stats/controller', payload=json.dumps(payload))

mqttPublisher = UnifiMqttPublisher()
mqttPublisher.run()
