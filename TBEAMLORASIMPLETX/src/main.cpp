#include <LoRa.h>
#include "LoRaBoards.h"
#include "ClosedCube_HDC1080.h"
#include <TinyGPSPlus.h>

#ifndef CONFIG_RADIO_FREQ
#define CONFIG_RADIO_FREQ           915.0
#endif
#ifndef CONFIG_RADIO_OUTPUT_POWER
#define CONFIG_RADIO_OUTPUT_POWER   17
#endif
#ifndef CONFIG_RADIO_BW
#define CONFIG_RADIO_BW             125.0
#endif


#if !defined(USING_SX1276) && !defined(USING_SX1278)
#error "LoRa example is only allowed to run SX1276/78. For other RF models, please run examples/RadioLibExamples"
#endif

int counter = 0;

ClosedCube_HDC1080 sensor;
//Cantidad de medidas de temperatura y humedad
const int count_i = 3;

float temperatures[count_i] = {};
float temp = 0;

float humidities[count_i] = {};
float humidity = 0;

//GPS
TinyGPSPlus gps;

void getHumidity();
void getTemperature();
float getMean(float measures[]);
static void smartDelay(unsigned long ms);

void setup()
{
    setupBoards();
    // When the power is turned on, a delay is required.
    delay(1500);

#ifdef  RADIO_TCXO_ENABLE
    pinMode(RADIO_TCXO_ENABLE, OUTPUT);
    digitalWrite(RADIO_TCXO_ENABLE, HIGH);
#endif

    Serial.println("LoRa Sender");
    LoRa.setPins(RADIO_CS_PIN, RADIO_RST_PIN, RADIO_DIO0_PIN);
    if (!LoRa.begin(CONFIG_RADIO_FREQ * 1000000)) {
        Serial.println("Starting LoRa failed!");
        while (1);
    }

    LoRa.setTxPower(CONFIG_RADIO_OUTPUT_POWER);

    LoRa.setSignalBandwidth(CONFIG_RADIO_BW * 1000);

    LoRa.setSpreadingFactor(10);

    LoRa.setPreambleLength(16);

    LoRa.setSyncWord(0xAB);

    LoRa.disableCrc();

    LoRa.disableInvertIQ();

    LoRa.setCodingRate4(7);
    
    Wire.begin(0,4);
    delay(100);
    Serial.begin(115200);
    delay(100);
    sensor.begin(0x40);
    delay(100);
    Serial1.begin(9600, SERIAL_8N1, 34, 12);
    
}

void loop()
{

    getTemperature();
    getHumidity();

    String message = "{\"id\": \"point16\" , \"lat\":" + String(gps.location.lat(), 6) + ", \"lon\":" + String(gps.location.lng(), 6) + ", \"temperatura\":" + String(temp) +", \"humedad\":" + String(humidity) + "}";
    Serial.println(message);
    // send packet
    LoRa.beginPacket();
    LoRa.print(message);
    LoRa.endPacket();

    delay(5000);
}


void getHumidity(){
  //Chirp de humedad
  float auxHumidity = 0;
  for (int i = 0; i < count_i; i++)
  {
    auxHumidity = sensor.readHumidity();
    smartDelay(100);
    humidities[i] = auxHumidity;
  }
   //Pruning humedad
  float mean = getMean(humidities);
  humidity = mean;
}
 
void getTemperature(){
  //Chirp de temperatura
  float auxTemp = 0;
  for (int i = 0; i < count_i; i++)
  {
    auxTemp = sensor.readTemperature();
    smartDelay(100);
    temperatures[i] = auxTemp;
  }
 //Pruning temperatura
  float mean = getMean(temperatures);
 
  temp= mean;
}
//Función para el pruning
float getMean(float measures[]){
 
  float total = 0;
 
  for (int i = 0; i < count_i; i++)
  {
    total += measures[i];
  }
 
  return (total/count_i);
 
}
 
static void smartDelay(unsigned long ms)
{
  
  unsigned long start = millis();
  do
  {
    while (Serial1.available())
      gps.encode(Serial1.read());
  } while (millis() - start < ms);
  
}
