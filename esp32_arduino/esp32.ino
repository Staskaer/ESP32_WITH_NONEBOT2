#include <WiFi.h>
#include <Arduino.h>
//wifi库用于入网，arduino库用于生成pwm
//由于esp32-arduino没有舵机pwm，所以要用LEDC来代替
//参见 https://docs.espressif.com/projects/arduino-esp32/en/latest/libraries.html

/*---------配置信息----------*/
// 必填参数
const char* ssid = "";                    // WiFi名
const char* password = "";                // WiFi密码
IPAddress local_IP(192, 168, 1, 202);     // esp32设备的ip地址，可以自由填写
IPAddress gateway(192, 168, 1, 1);        // 网关，填路由器地址，一般就是这个
IPAddress subnet(255, 255, 0, 0);         // 子网掩码，一般不变

// 可选参数
const int LED = 4;                        // LED灯-pwm指示
const int LED_C = 3;                      // LED灯-连接指示
const int PWM = 6;                        // pwm信号的输出端
IPAddress primaryDNS(192, 168, 1, 1);     // DSN服务，可以填路由器地址，或不填
IPAddress secondaryDNS(192, 168, 1, 1);   // DSN服务，可以填路由器地址，或不填

/*---------全局变量----------*/
WiFiServer server(80);      // 配置web服务器端口
int mode = 0;               // 记录目前开关状态
uint32_t channel = 5;       // 使用的ledc通道
String header;              // 字符串

int calculatePWM(int degree)
// 根据角度计算占空比
{ //0-180度
  //20ms周期，高电平0.5-2.5ms，对应0-180度角度
  const float deadZone = 25.6;
  const float max = 128;
  if (degree < 0)
    degree = 0;
  if (degree > 180)
    degree = 180;
  return (int)(((max - deadZone) / 180) * degree + deadZone);
}


void setup() 
{
  ledcSetup(channel, 50, 10);           // ledc通道， 50Hz，10位解析度
  ledcAttachPin(PWM, channel);          // 定义为通道的输出引脚
  ledcWrite(channel,calculatePWM(90));  // 输出PWM，先复位到90°
  
  Serial.begin(115200);                 // 串口
  
  pinMode(LED, OUTPUT);
  digitalWrite(LED, LOW);               // 初始化并关闭LED
  pinMode(LED_C, OUTPUT);
  digitalWrite(LED_C, LOW);             // 初始化并关闭LED
  
  // 连接到路由器
  if (!WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS)) 
  {
    Serial.println("STA Failed to configure");
  }

  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  digitalWrite(LED_C, HIGH);
  while (WiFi.status() != WL_CONNECTED) 
  {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected.");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
  server.begin();
  digitalWrite(LED_C, LOW);
}



void loop()
{
  // 防止地址租期过期导致无法访问
  // （没试过能不能用）
  if (WiFi.status() != WL_CONNECTED) 
  {
    WiFi.begin(ssid, password);
    digitalWrite(LED_C, HIGH);
    Serial.print("connecting...");
  }
  while (WiFi.status() != WL_CONNECTED) 
  {
    delay(500);
    Serial.print(".");
  }
  digitalWrite(LED_C, LOW);

  // 正式功能部分
  WiFiClient client = server.available();   

  if (client) 
  {                                         // 连接
    Serial.println("New Client.");          // 串口打印
    String currentLine = "";                // 准备接受数据
    while (client.connected()) 
    {            
      if (client.available()) 
      {             
        char c = client.read();             
        Serial.write(c);
        header += c;
        if (c == '\n') 
        {           
          /*处理请求*/         
          if (currentLine.length() == 0) 
          {
            client.println("HTTP/1.1 200 OK");
            client.println("Content-type:text/html");
            client.println("Connection: close");
            client.println();
            
            // 处理对应的请求
            if (header.indexOf("GET /on") >= 0) 
            {
              digitalWrite(LED, HIGH);
              ledcWrite(channel,calculatePWM(40)); // 输出PWM
              mode = 1;
              delay(300);
              ledcWrite(channel,calculatePWM(90)); // 输出PWM

              digitalWrite(LED, LOW);
              
            }
            else if (header.indexOf("GET /off") >= 0) 
            {
              digitalWrite(LED, HIGH);
              ledcWrite(channel,calculatePWM(140)); // 输出PWM
              mode = 0;
              delay(300);
              ledcWrite(channel,calculatePWM(90)); // 输出PWM
              digitalWrite(LED, LOW);
            }
            else if (header.indexOf("GET /conf") >= 0) 
            {
              //返回当前状态，用于同步
              client.println(String(mode));
            }
            /*结束请求*/
            break;
          } 
          else 
          {
            currentLine = "";
          }
        } 
        else if (c != '\r') 
        { 
          currentLine += c;
        }
      }
    }
    // 重置变量并关闭连接
    header = "";
    client.stop();
    Serial.println("Client disconnected.");
    Serial.println("");
  }
}
