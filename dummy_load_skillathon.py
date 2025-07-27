from firebase_admin import firestore
from datetime import datetime
import pytz
from django.contrib.auth import get_user_model
from assessments.models import Learner, SkillathonEvent, Institution, EbekUser

db = firestore.client()


student_data = {
  "REBIKA": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 17,
      "Grade": "D",
      "Percentage": "68.00%",
      "Critical Steps Missed": 1,
      "Institution": "EBM College of Nursing"
    }
  ],
  "NIRUPAM": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 11,
      "Grade": "E",
      "Percentage": "57.89%",
      "Critical Steps Missed": 2,
      "Institution": "EBM College of Nursing"
    }
  ],
  "ROHIT KUMAR SAHA": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "21.05%",
      "Critical Steps Missed": 3,
      "Institution": "EBM College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "11.11%",
      "Critical Steps Missed": 4,
      "Institution": "EBM College of Nursing"
    }
  ],
  "YONA UMESH": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "33.33%",
      "Critical Steps Missed": 3,
      "Institution": "EBM College of Nursing"
    }
  ],
  "SAHIL": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 15,
      "Grade": "D",
      "Percentage": "60.00%",
      "Critical Steps Missed": 1,
      "Institution": "EBM College of Nursing"
    }
  ],
  "MADHUR": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "EBM College of Nursing"
    }
  ],
  "G SWATHI": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "33.33%",
      "Critical Steps Missed": 3,
      "Institution": "EBM College of Nursing"
    }
  ],
  "KUNAL": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.26%",
      "Critical Steps Missed": 3,
      "Institution": "EBM College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 18,
      "Grade": "C",
      "Percentage": "72.00%",
      "Critical Steps Missed": 1,
      "Institution": "EBM College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "EBM College of Nursing"
    }
  ],
  "BABLU SHARMA": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 18,
      "Grade": "C",
      "Percentage": "72.00%",
      "Critical Steps Missed": 1,
      "Institution": "EBM College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "EBM College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "15.79%",
      "Critical Steps Missed": 3,
      "Institution": "EBM College of Nursing"
    }
  ],
  "PRIYA": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "15.79%",
      "Critical Steps Missed": 3,
      "Institution": "EBM College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "EBM College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 24,
      "Grade": "A",
      "Percentage": "96.00%",
      "Critical Steps Missed": 0,
      "Institution": "EBM College of Nursing"
    }
  ],
  "SONI GOGOI": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 22,
      "Grade": "B",
      "Percentage": "88.00%",
      "Critical Steps Missed": 0,
      "Institution": "EBM College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 11,
      "Grade": "D",
      "Percentage": "61.11%",
      "Critical Steps Missed": 2,
      "Institution": "EBM College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 14,
      "Grade": "C",
      "Percentage": "73.68%",
      "Critical Steps Missed": 1,
      "Institution": "EBM College of Nursing"
    }
  ],
  "S ADIL": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 17,
      "Grade": "A",
      "Percentage": "94.44%",
      "Critical Steps Missed": 0,
      "Institution": "EBM College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "21.05%",
      "Critical Steps Missed": 3,
      "Institution": "EBM College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 23,
      "Grade": "A",
      "Percentage": "92.00%",
      "Critical Steps Missed": 0,
      "Institution": "EBM College of Nursing"
    }
  ],
  "SUHASINI B": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "26.32%",
      "Critical Steps Missed": 3,
      "Institution": "EBM College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 11,
      "Grade": "E",
      "Percentage": "44.00%",
      "Critical Steps Missed": 2,
      "Institution": "EBM College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "EBM College of Nursing"
    }
  ],
  "Swathi": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "4.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh School of Nursing"
    }
  ],
  "G Mounika": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "Neelima CON"
    }
  ],
  "Pravalika": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "4.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh School of Nursing"
    }
  ],
  "Sowjanya": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "21.05%",
      "Critical Steps Missed": 2,
      "Institution": "Durgabai Deshmukh School of Nursing"
    }
  ],
  "Madhavi": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "11.11%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh School of Nursing"
    }
  ],
  "Vrshala": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 0,
      "Grade": "E",
      "Percentage": "0.00%",
      "Critical Steps Missed": 3,
      "Institution": "Neelima CON"
    }
  ],
  "M Poojitha": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "8.00%",
      "Critical Steps Missed": 3,
      "Institution": "Neelima CON"
    }
  ],
  "Amulya": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "11.11%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh School of Nursing"
    }
  ],
  "Aravind Kumar": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "12.00%",
      "Critical Steps Missed": 3,
      "Institution": "Neelima CON"
    }
  ],
  "Chandana": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "15.79%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh School of Nursing"
    }
  ],
  "Sowmya": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "22.22%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh School of Nursing"
    }
  ],
  "Hrushikesh": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "10.53%",
      "Critical Steps Missed": 3,
      "Institution": "Neelima CON"
    }
  ],
  "Arshitha": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "12.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh School of Nursing"
    }
  ],
  "Swetha": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh School of Nursing"
    }
  ],
  "Sruthi": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "15.79%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh School of Nursing"
    }
  ],
  "Chitra": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "12.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh School of Nursing"
    }
  ],
  "Vijetha": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh School of Nursing"
    }
  ],
  "Quthbuddin": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "15.79%",
      "Critical Steps Missed": 3,
      "Institution": "Neelima CON"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "12.00%",
      "Critical Steps Missed": 3,
      "Institution": "Neelima CON"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 14,
      "Grade": "C",
      "Percentage": "77.78%",
      "Critical Steps Missed": 1,
      "Institution": "Neelima CON"
    }
  ],
  "Govada Preethi": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "12.00%",
      "Critical Steps Missed": 3,
      "Institution": "Neelima CON"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "11.11%",
      "Critical Steps Missed": 4,
      "Institution": "Neelima CON"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.26%",
      "Critical Steps Missed": 3,
      "Institution": "Neelima CON"
    }
  ],
  "Blesson": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 0,
      "Grade": "E",
      "Percentage": "0.00%",
      "Critical Steps Missed": 3,
      "Institution": "Neelima CON"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "33.33%",
      "Critical Steps Missed": 3,
      "Institution": "Neelima CON"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 13,
      "Grade": "E",
      "Percentage": "52.00%",
      "Critical Steps Missed": 1,
      "Institution": "Neelima CON"
    }
  ],
  "Santripti Sharma": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 10,
      "Grade": "E",
      "Percentage": "40.00%",
      "Critical Steps Missed": 2,
      "Institution": "Neelima CON"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 10,
      "Grade": "E",
      "Percentage": "55.56%",
      "Critical Steps Missed": 2,
      "Institution": "Neelima CON"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 14,
      "Grade": "C",
      "Percentage": "73.68%",
      "Critical Steps Missed": 1,
      "Institution": "Neelima CON"
    }
  ],
  "CH Nandhini": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "36.84%",
      "Critical Steps Missed": 2,
      "Institution": "Neelima CON"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 0,
      "Grade": "E",
      "Percentage": "0.00%",
      "Critical Steps Missed": 3,
      "Institution": "Neelima CON"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "11.11%",
      "Critical Steps Missed": 4,
      "Institution": "Neelima CON"
    }
  ],
  "Neha": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 0,
      "Grade": "E",
      "Percentage": "0.00%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh School of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 0,
      "Grade": "E",
      "Percentage": "0.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh School of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "4.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh School of Nursing"
    }
  ],
  "Solitha": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "24.00%",
      "Critical Steps Missed": 3,
      "Institution": "Sita Ramaiah CON"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "11.11%",
      "Critical Steps Missed": 4,
      "Institution": "Sita Ramaiah CON"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.26%",
      "Critical Steps Missed": 3,
      "Institution": "Sita Ramaiah CON"
    }
  ],
  "Mahendra Kumar": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "15.79%",
      "Critical Steps Missed": 3,
      "Institution": "Sita Ramaiah CON"
    }
  ],
  "Sohail": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 18,
      "Grade": "A",
      "Percentage": "100.00%",
      "Critical Steps Missed": 0,
      "Institution": "Sita Ramaiah CON"
    }
  ],
  "B Vinod": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "20.00%",
      "Critical Steps Missed": 3,
      "Institution": "Sita Ramaiah CON"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "38.89%",
      "Critical Steps Missed": 3,
      "Institution": "Sita Ramaiah CON"
    }
  ],
  "Arshiya": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 15,
      "Grade": "C",
      "Percentage": "78.95%",
      "Critical Steps Missed": 1,
      "Institution": "Sita Ramaiah CON"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "24.00%",
      "Critical Steps Missed": 3,
      "Institution": "Sita Ramaiah CON"
    }
  ],
  "D Mahesh": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "24.00%",
      "Critical Steps Missed": 3,
      "Institution": "Sita Ramaiah CON"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 11,
      "Grade": "D",
      "Percentage": "61.11%",
      "Critical Steps Missed": 2,
      "Institution": "Sita Ramaiah CON"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 11,
      "Grade": "E",
      "Percentage": "57.89%",
      "Critical Steps Missed": 2,
      "Institution": "Sita Ramaiah CON"
    }
  ],
  "B Sai Kumar": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 10,
      "Grade": "E",
      "Percentage": "52.63%",
      "Critical Steps Missed": 1,
      "Institution": "Sita Ramaiah CON"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 8,
      "Grade": "E",
      "Percentage": "32.00%",
      "Critical Steps Missed": 3,
      "Institution": "Sita Ramaiah CON"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "33.33%",
      "Critical Steps Missed": 3,
      "Institution": "Sita Ramaiah CON"
    }
  ],
  "A Harish": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 9,
      "Grade": "E",
      "Percentage": "50.00%",
      "Critical Steps Missed": 3,
      "Institution": "Sita Ramaiah CON"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "10.53%",
      "Critical Steps Missed": 3,
      "Institution": "Sita Ramaiah CON"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "24.00%",
      "Critical Steps Missed": 3,
      "Institution": "Sita Ramaiah CON"
    }
  ],
  "R Vijay": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 15,
      "Grade": "C",
      "Percentage": "78.95%",
      "Critical Steps Missed": 1,
      "Institution": "Sita Ramaiah CON"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 9,
      "Grade": "E",
      "Percentage": "36.00%",
      "Critical Steps Missed": 2,
      "Institution": "Sita Ramaiah CON"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.56%",
      "Critical Steps Missed": 4,
      "Institution": "Sita Ramaiah CON"
    }
  ],
  "Veeranna": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "24.00%",
      "Critical Steps Missed": 3,
      "Institution": "Sita Ramaiah CON"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "11.11%",
      "Critical Steps Missed": 4,
      "Institution": "Sita Ramaiah CON"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 14,
      "Grade": "C",
      "Percentage": "73.68%",
      "Critical Steps Missed": 1,
      "Institution": "Sita Ramaiah CON"
    }
  ],
  "ROSE MARIYA JOSE": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 10,
      "Grade": "E",
      "Percentage": "40.00%",
      "Critical Steps Missed": 2,
      "Institution": "Vijay Marie College of Nursing"
    }
  ],
  "MUSHIBOINA KIRANMAI": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "20.00%",
      "Critical Steps Missed": 3,
      "Institution": "CARE COLLEGE OF NURSING"
    }
  ],
  "ABHAYA PUL": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "31.58%",
      "Critical Steps Missed": 2,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    }
  ],
  "CHAKALI SANDHYA": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 9,
      "Grade": "E",
      "Percentage": "50.00%",
      "Critical Steps Missed": 3,
      "Institution": "CARE COLLEGE OF NURSING"
    }
  ],
  "ASHANPALLY SAVITHA": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "15.79%",
      "Critical Steps Missed": 3,
      "Institution": "CARE COLLEGE OF NURSING"
    }
  ],
  "AMRITHA RAJENDRAN": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "24.00%",
      "Critical Steps Missed": 3,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    }
  ],
  "NENAVATH SONIYA": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "36.84%",
      "Critical Steps Missed": 2,
      "Institution": "CARE COLLEGE OF NURSING"
    }
  ],
  "MARIA KURIAKOSE": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 12,
      "Grade": "E",
      "Percentage": "48.00%",
      "Critical Steps Missed": 2,
      "Institution": "CARE COLLEGE OF NURSING"
    }
  ],
  "ANUPRIYA MOHAN": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 10,
      "Grade": "E",
      "Percentage": "55.56%",
      "Critical Steps Missed": 2,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    }
  ],
  "KAVYA MOL K R": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "22.22%",
      "Critical Steps Missed": 4,
      "Institution": "CARE COLLEGE OF NURSING"
    }
  ],
  "ELIZABETH SHINTO": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.26%",
      "Critical Steps Missed": 3,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    }
  ],
  "ALBY MARTIN": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 11,
      "Grade": "E",
      "Percentage": "44.00%",
      "Critical Steps Missed": 2,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    }
  ],
  "FEBA ROY GEORGE": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "22.22%",
      "Critical Steps Missed": 4,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    }
  ],
  "VICTORIA NAIK KOLA": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "33.33%",
      "Critical Steps Missed": 4,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    }
  ],
  "AFSHAN NEWEED": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "20.00%",
      "Critical Steps Missed": 3,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    }
  ],
  "S VINODHI": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "27.78%",
      "Critical Steps Missed": 4,
      "Institution": "CARE COLLEGE OF NURSING"
    }
  ],
  "MARIYATTE SHINTO": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 8,
      "Grade": "E",
      "Percentage": "42.11%",
      "Critical Steps Missed": 2,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    }
  ],
  "SONA M KURIAKOSE": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 8,
      "Grade": "E",
      "Percentage": "44.44%",
      "Critical Steps Missed": 3,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    }
  ],
  "ANUMOL SONY": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "21.05%",
      "Critical Steps Missed": 3,
      "Institution": "CARE COLLEGE OF NURSING"
    }
  ],
  "BANOTH ANUSHA": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "27.78%",
      "Critical Steps Missed": 4,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    }
  ],
  "AISWARYA JAYAGOPAL": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 8,
      "Grade": "E",
      "Percentage": "32.00%",
      "Critical Steps Missed": 3,
      "Institution": "CARE COLLEGE OF NURSING"
    }
  ],
  "PATHALA NANDINI": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "15.79%",
      "Critical Steps Missed": 3,
      "Institution": "CARE COLLEGE OF NURSING"
    }
  ],
  "ADHARLA AKANKSHA": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "38.89%",
      "Critical Steps Missed": 3,
      "Institution": "CARE COLLEGE OF NURSING"
    }
  ],
  "THOKALA PAVANI": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "20.00%",
      "Critical Steps Missed": 3,
      "Institution": "CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "38.89%",
      "Critical Steps Missed": 3,
      "Institution": "CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.26%",
      "Critical Steps Missed": 3,
      "Institution": "CARE COLLEGE OF NURSING"
    }
  ],
  "DHONVAN AKHILA": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 8,
      "Grade": "E",
      "Percentage": "44.44%",
      "Critical Steps Missed": 3,
      "Institution": "CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.26%",
      "Critical Steps Missed": 3,
      "Institution": "CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "28.00%",
      "Critical Steps Missed": 3,
      "Institution": "CARE COLLEGE OF NURSING"
    }
  ],
  "VASALA NANDINI": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 13,
      "Grade": "E",
      "Percentage": "52.00%",
      "Critical Steps Missed": 2,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 8,
      "Grade": "E",
      "Percentage": "44.44%",
      "Critical Steps Missed": 3,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    }
  ],
  "E K REBEKAH DAYANIDHI": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 11,
      "Grade": "E",
      "Percentage": "44.00%",
      "Critical Steps Missed": 2,
      "Institution": "CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "27.78%",
      "Critical Steps Missed": 3,
      "Institution": "CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 9,
      "Grade": "E",
      "Percentage": "47.37%",
      "Critical Steps Missed": 2,
      "Institution": "CARE COLLEGE OF NURSING"
    }
  ],
  "JEMI JOSEPH": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "10.53%",
      "Critical Steps Missed": 3,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 8,
      "Grade": "E",
      "Percentage": "32.00%",
      "Critical Steps Missed": 3,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "11.11%",
      "Critical Steps Missed": 4,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    }
  ],
  "KHUSHI MALLOJWAR": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "36.84%",
      "Critical Steps Missed": 2,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "27.78%",
      "Critical Steps Missed": 3,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 16,
      "Grade": "D",
      "Percentage": "64.00%",
      "Critical Steps Missed": 1,
      "Institution": "CARE NAMPALLY COLLEGE OF NURSING"
    }
  ],
  "Jannath": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "28.00%",
      "Critical Steps Missed": 3,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "Habeeb": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 11,
      "Grade": "E",
      "Percentage": "57.89%",
      "Critical Steps Missed": 1,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "Munazza": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "33.33%",
      "Critical Steps Missed": 3,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "Yasmeen Begum": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "11.11%",
      "Critical Steps Missed": 4,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "Helmina": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "12.00%",
      "Critical Steps Missed": 3,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "Mehmooda": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "31.58%",
      "Critical Steps Missed": 2,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "Husan": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "38.89%",
      "Critical Steps Missed": 3,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "K Shilpa Kiran": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "16.00%",
      "Critical Steps Missed": 3,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "22.22%",
      "Critical Steps Missed": 4,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "31.58%",
      "Critical Steps Missed": 2,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "Aruri Pavithra": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "10.53%",
      "Critical Steps Missed": 3,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 9,
      "Grade": "E",
      "Percentage": "36.00%",
      "Critical Steps Missed": 2,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "27.78%",
      "Critical Steps Missed": 3,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "R Ramanika": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "38.89%",
      "Critical Steps Missed": 3,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 13,
      "Grade": "D",
      "Percentage": "68.42%",
      "Critical Steps Missed": 1,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "4.00%",
      "Critical Steps Missed": 3,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "Sareen Sultana": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 15,
      "Grade": "C",
      "Percentage": "78.95%",
      "Critical Steps Missed": 1,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "12.00%",
      "Critical Steps Missed": 3,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "Sikdar Shahifa": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 11,
      "Grade": "E",
      "Percentage": "44.00%",
      "Critical Steps Missed": 2,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "11.11%",
      "Critical Steps Missed": 4,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "31.58%",
      "Critical Steps Missed": 2,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "Taniya": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "11.11%",
      "Critical Steps Missed": 4,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 18,
      "Grade": "A",
      "Percentage": "94.74%",
      "Critical Steps Missed": 0,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 8,
      "Grade": "E",
      "Percentage": "32.00%",
      "Critical Steps Missed": 3,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "Neena Hameed": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "8.00%",
      "Critical Steps Missed": 3,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 11,
      "Grade": "E",
      "Percentage": "57.89%",
      "Critical Steps Missed": 1,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "Juveriya": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "31.58%",
      "Critical Steps Missed": 2,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "12.00%",
      "Critical Steps Missed": 3,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.56%",
      "Critical Steps Missed": 4,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "Rownaq Afroze": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "27.78%",
      "Critical Steps Missed": 4,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 14,
      "Grade": "C",
      "Percentage": "73.68%",
      "Critical Steps Missed": 0,
      "Institution": "Muslim Maternity College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "16.00%",
      "Critical Steps Missed": 3,
      "Institution": "Muslim Maternity College of Nursing"
    }
  ],
  "G AISHWARYA": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 0,
      "Grade": "E",
      "Percentage": "0.00%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "K LAVANYA": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "N PRATIBHA": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 14,
      "Grade": "E",
      "Percentage": "56.00%",
      "Critical Steps Missed": 1,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "K KAVYA": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "G PREETHI": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "21.05%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "K MAHESWARI": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 15,
      "Grade": "D",
      "Percentage": "60.00%",
      "Critical Steps Missed": 1,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "E AKSHAYA": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "22.22%",
      "Critical Steps Missed": 4,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "D SRIVIDHYA": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "12.00%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "10.53%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "E LAVANYA": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "21.05%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "R RANI": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 13,
      "Grade": "C",
      "Percentage": "72.22%",
      "Critical Steps Missed": 1,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "N MADHURI": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "12.00%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 8,
      "Grade": "E",
      "Percentage": "44.44%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "P SHASHI PRIYA": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "12.00%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "P PRAVALIKA": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "10.53%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "G NARMADA": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "4.00%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "M HARISHA": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "Yashoda College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "36.84%",
      "Critical Steps Missed": 2,
      "Institution": "Yashoda College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "16.00%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "K SHARON ROJA": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "21.05%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "20.00%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "L BHUMIKA": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 14,
      "Grade": "E",
      "Percentage": "56.00%",
      "Critical Steps Missed": 1,
      "Institution": "Yashoda College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "Yashoda College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "15.79%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "S MADHAVI": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "16.00%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "27.78%",
      "Critical Steps Missed": 4,
      "Institution": "Yashoda College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "10.53%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "K SWETHA": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 19,
      "Grade": "A",
      "Percentage": "100.00%",
      "Critical Steps Missed": 0,
      "Institution": "Yashoda College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 15,
      "Grade": "D",
      "Percentage": "60.00%",
      "Critical Steps Missed": 1,
      "Institution": "Yashoda College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "27.78%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "K AKHILA": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "Yashoda College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "21.05%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "8.00%",
      "Critical Steps Missed": 3,
      "Institution": "Yashoda College of Nursing"
    }
  ],
  "Sohphia Sultana": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 15,
      "Grade": "C",
      "Percentage": "78.95%",
      "Critical Steps Missed": 0,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "C Aruna": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.56%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "A Aparna": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "8.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "Ks Varalaxmi": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.56%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "D Anitha": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "22.22%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "B Suma": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "16.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "G Harshini": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "11.11%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "K Shailaja": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 9,
      "Grade": "E",
      "Percentage": "50.00%",
      "Critical Steps Missed": 2,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "B Priyanka": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "38.89%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "N Akshaya": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "12.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "S Maneesha": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.56%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "B Shanthipriya": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "12.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "A Nagasri": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.56%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "L Keerthana": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 0,
      "Grade": "E",
      "Percentage": "0.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "4.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "11.11%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "T Arundhathi": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.56%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "Sk Shakura": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "4.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "11.11%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "26.32%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "Ch Archana": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "11.11%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "15.79%",
      "Critical Steps Missed": 2,
      "Institution": "Durgabai Deshmukh College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "8.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "S Sadhana": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "4.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "27.78%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "36.84%",
      "Critical Steps Missed": 2,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "A Sanjana": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 18,
      "Grade": "A",
      "Percentage": "94.74%",
      "Critical Steps Missed": 0,
      "Institution": "Durgabai Deshmukh College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "16.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "27.78%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "M Soujanya": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "Durgabai Deshmukh College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.26%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "8.00%",
      "Critical Steps Missed": 3,
      "Institution": "Durgabai Deshmukh College of Nursing"
    }
  ],
  "INDUR RAKSHITHA": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "21.05%",
      "Critical Steps Missed": 3,
      "Institution": "Medicity College of Nursing"
    }
  ],
  "RAMAVATH BHAGAVAN": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 9,
      "Grade": "E",
      "Percentage": "36.00%",
      "Critical Steps Missed": 2,
      "Institution": "Medicity College of Nursing"
    }
  ],
  "GANGADHARI AKHIL": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 14,
      "Grade": "C",
      "Percentage": "77.78%",
      "Critical Steps Missed": 1,
      "Institution": "Medicity College of Nursing"
    }
  ],
  "G. SAIPRIYA": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "Pier Giorgio Frassati College of Nursing"
    }
  ],
  "R. PRIYANKA": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "20.00%",
      "Critical Steps Missed": 3,
      "Institution": "Pier Giorgio Frassati College of Nursing"
    }
  ],
  "DAVULA SANDEEP": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 10,
      "Grade": "E",
      "Percentage": "55.56%",
      "Critical Steps Missed": 2,
      "Institution": "Medicity College of Nursing"
    }
  ],
  "B. KALYANI": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "15.79%",
      "Critical Steps Missed": 3,
      "Institution": "Pier Giorgio Frassati College of Nursing"
    }
  ],
  "NGOJEN RANGWANG": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 8,
      "Grade": "E",
      "Percentage": "44.44%",
      "Critical Steps Missed": 3,
      "Institution": "Pier Giorgio Frassati College of Nursing"
    }
  ],
  "BYAGARI NARENDAR": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 11,
      "Grade": "E",
      "Percentage": "44.00%",
      "Critical Steps Missed": 2,
      "Institution": "Medicity College of Nursing"
    }
  ],
  "MUPPU ANVESH": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "22.22%",
      "Critical Steps Missed": 4,
      "Institution": "Medicity College of Nursing"
    }
  ],
  "K. UMADEVI": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 0,
      "Grade": "E",
      "Percentage": "0.00%",
      "Critical Steps Missed": 3,
      "Institution": "Pier Giorgio Frassati College of Nursing"
    }
  ],
  "B.SAGAR RESHMA": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.56%",
      "Critical Steps Missed": 4,
      "Institution": "Pier Giorgio Frassati College of Nursing"
    }
  ],
  "SABHAVATH RAMU": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 9,
      "Grade": "E",
      "Percentage": "36.00%",
      "Critical Steps Missed": 2,
      "Institution": "Medicity College of Nursing"
    }
  ],
  "SHAIK SADHIK": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "10.53%",
      "Critical Steps Missed": 3,
      "Institution": "Medicity College of Nursing"
    }
  ],
  "AJMIRA TEJAPAL NAYAK": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "33.33%",
      "Critical Steps Missed": 3,
      "Institution": "Medicity College of Nursing"
    }
  ],
  "ANVIYA SHAJU": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.26%",
      "Critical Steps Missed": 3,
      "Institution": "Pier Giorgio Frassati College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 11,
      "Grade": "E",
      "Percentage": "44.00%",
      "Critical Steps Missed": 2,
      "Institution": "Pier Giorgio Frassati College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "22.22%",
      "Critical Steps Missed": 4,
      "Institution": "Pier Giorgio Frassati College of Nursing"
    }
  ],
  "CH. ANUHYA": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "16.00%",
      "Critical Steps Missed": 3,
      "Institution": "Pier Giorgio Frassati College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "22.22%",
      "Critical Steps Missed": 4,
      "Institution": "Pier Giorgio Frassati College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "10.53%",
      "Critical Steps Missed": 3,
      "Institution": "Pier Giorgio Frassati College of Nursing"
    }
  ],
  "P. ASHRITHA": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "22.22%",
      "Critical Steps Missed": 4,
      "Institution": "Pier Giorgio Frassati College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "31.58%",
      "Critical Steps Missed": 2,
      "Institution": "Pier Giorgio Frassati College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 11,
      "Grade": "E",
      "Percentage": "44.00%",
      "Critical Steps Missed": 2,
      "Institution": "Pier Giorgio Frassati College of Nursing"
    }
  ],
  "KOKKONDA ABHINAY": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 9,
      "Grade": "E",
      "Percentage": "47.37%",
      "Critical Steps Missed": 2,
      "Institution": "Medicity College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 21,
      "Grade": "B",
      "Percentage": "84.00%",
      "Critical Steps Missed": 0,
      "Institution": "Medicity College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "33.33%",
      "Critical Steps Missed": 3,
      "Institution": "Medicity College of Nursing"
    }
  ],
  "RATHOD RANJITH NAYAK": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 17,
      "Grade": "D",
      "Percentage": "68.00%",
      "Critical Steps Missed": 1,
      "Institution": "Medicity College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "Medicity College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 11,
      "Grade": "E",
      "Percentage": "57.89%",
      "Critical Steps Missed": 1,
      "Institution": "Medicity College of Nursing"
    }
  ],
  "SUFIYAN SALIK": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.56%",
      "Critical Steps Missed": 4,
      "Institution": "Medicity College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.26%",
      "Critical Steps Missed": 3,
      "Institution": "Medicity College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "4.00%",
      "Critical Steps Missed": 3,
      "Institution": "Medicity College of Nursing"
    }
  ],
  "YAMAGANI SWEETY": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "15.79%",
      "Critical Steps Missed": 3,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "20.00%",
      "Critical Steps Missed": 3,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 12,
      "Grade": "D",
      "Percentage": "66.67%",
      "Critical Steps Missed": 2,
      "Institution": "Vijay Marie College of Nursing"
    }
  ],
  "DARIPALLI MANUSHA": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 11,
      "Grade": "E",
      "Percentage": "44.00%",
      "Critical Steps Missed": 2,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 10,
      "Grade": "E",
      "Percentage": "55.56%",
      "Critical Steps Missed": 2,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "36.84%",
      "Critical Steps Missed": 2,
      "Institution": "Vijay Marie College of Nursing"
    }
  ],
  "ALLI BHAVYA": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "38.89%",
      "Critical Steps Missed": 3,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 13,
      "Grade": "D",
      "Percentage": "68.42%",
      "Critical Steps Missed": 1,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 15,
      "Grade": "D",
      "Percentage": "60.00%",
      "Critical Steps Missed": 2,
      "Institution": "Vijay Marie College of Nursing"
    }
  ],
  "TERESA SAPRIINAMEI": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 19,
      "Grade": "A",
      "Percentage": "100.00%",
      "Critical Steps Missed": 0,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 19,
      "Grade": "C",
      "Percentage": "76.00%",
      "Critical Steps Missed": 1,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 18,
      "Grade": "A",
      "Percentage": "100.00%",
      "Critical Steps Missed": 0,
      "Institution": "Vijay Marie College of Nursing"
    }
  ],
  "KAROLLA SWAPNA": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 17,
      "Grade": "D",
      "Percentage": "68.00%",
      "Critical Steps Missed": 1,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 10,
      "Grade": "E",
      "Percentage": "55.56%",
      "Critical Steps Missed": 2,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 14,
      "Grade": "C",
      "Percentage": "73.68%",
      "Critical Steps Missed": 1,
      "Institution": "Vijay Marie College of Nursing"
    }
  ],
  "GUJJI SWAPNA": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "38.89%",
      "Critical Steps Missed": 3,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "26.32%",
      "Critical Steps Missed": 2,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 10,
      "Grade": "E",
      "Percentage": "40.00%",
      "Critical Steps Missed": 2,
      "Institution": "Vijay Marie College of Nursing"
    }
  ],
  "FARHEEN BEGUM": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 10,
      "Grade": "E",
      "Percentage": "55.56%",
      "Critical Steps Missed": 2,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "15.79%",
      "Critical Steps Missed": 3,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "16.00%",
      "Critical Steps Missed": 3,
      "Institution": "Vijay Marie College of Nursing"
    }
  ],
  "V . AMBIKA": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 19,
      "Grade": "A",
      "Percentage": "100.00%",
      "Critical Steps Missed": 0,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 12,
      "Grade": "E",
      "Percentage": "48.00%",
      "Critical Steps Missed": 2,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "38.89%",
      "Critical Steps Missed": 3,
      "Institution": "Vijay Marie College of Nursing"
    }
  ],
  "NALAM BHAVANI": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "24.00%",
      "Critical Steps Missed": 3,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 14,
      "Grade": "C",
      "Percentage": "77.78%",
      "Critical Steps Missed": 1,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 9,
      "Grade": "E",
      "Percentage": "47.37%",
      "Critical Steps Missed": 2,
      "Institution": "Vijay Marie College of Nursing"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 9,
      "Grade": "E",
      "Percentage": "47.37%",
      "Critical Steps Missed": 3,
      "Institution": "Vijay Marie College of Nursing"
    }
  ],
  "P. Nithish kumar": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "15.79%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 11,
      "Grade": "E",
      "Percentage": "44.00%",
      "Critical Steps Missed": 2,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 13,
      "Grade": "C",
      "Percentage": "72.22%",
      "Critical Steps Missed": 1,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    }
  ],
  "A. Srinu": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 8,
      "Grade": "E",
      "Percentage": "44.44%",
      "Critical Steps Missed": 2,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "21.05%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "16.00%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    }
  ],
  "B. Sampath": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "24.00%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "38.89%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.26%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    }
  ],
  "Deepika": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 0,
      "Grade": "E",
      "Percentage": "0.00%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "20.00%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    }
  ],
  "B. Esther davina": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 10,
      "Grade": "E",
      "Percentage": "40.00%",
      "Critical Steps Missed": 2,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "21.05%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    }
  ],
  "Aleena biju": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 8,
      "Grade": "E",
      "Percentage": "44.44%",
      "Critical Steps Missed": 2,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "15.79%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "16.00%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    }
  ],
  "B. Venkat Ramulu": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 9,
      "Grade": "E",
      "Percentage": "47.37%",
      "Critical Steps Missed": 2,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "16.00%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 16,
      "Grade": "B",
      "Percentage": "88.89%",
      "Critical Steps Missed": 0,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    }
  ],
  "Ajay Murugesh A M": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 13,
      "Grade": "E",
      "Percentage": "52.00%",
      "Critical Steps Missed": 2,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 3,
      "Grade": "E",
      "Percentage": "16.67%",
      "Critical Steps Missed": 4,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "21.05%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    }
  ],
  "Jakkula sai kumar": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "33.33%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "31.58%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "24.00%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    }
  ],
  "V. Rajalakshmi": [
    {
      "Procedure Name": "Communication skills",
      "Total Score": 1,
      "Grade": "E",
      "Percentage": "5.26%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "16.00%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 9,
      "Grade": "E",
      "Percentage": "50.00%",
      "Critical Steps Missed": 2,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    }
  ],
  "K. Sravani": [
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "16.00%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 7,
      "Grade": "E",
      "Percentage": "38.89%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 6,
      "Grade": "E",
      "Percentage": "31.58%",
      "Critical Steps Missed": 2,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    }
  ],
  "T. Vishaka": [
    {
      "Procedure Name": "Cardiopulmonary Resuscitation",
      "Total Score": 4,
      "Grade": "E",
      "Percentage": "22.22%",
      "Critical Steps Missed": 4,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Communication skills",
      "Total Score": 5,
      "Grade": "E",
      "Percentage": "26.32%",
      "Critical Steps Missed": 2,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    },
    {
      "Procedure Name": "Intradermal Injection",
      "Total Score": 2,
      "Grade": "E",
      "Percentage": "8.00%",
      "Critical Steps Missed": 3,
      "Institution": "VIJAYA HEALTH CARE COLLEGE OF NURSING"
    }
  ]
}


SKILLATHON_NAME = "Hyderabad Skillathon"
today = datetime.now(pytz.timezone("Asia/Kolkata"))

for student_name, procedures in student_data.items():
    for proc in procedures:
        proc_name = proc["Procedure Name"]
        institution = proc["Institution"]
        marks = proc["Total Score"]
        critical_missed = proc["Critical Steps Missed"]

        # Find user in Firestore by name and institution
        users_query = db.collection('Users') \
            .where('name', '==', student_name) \
            .limit(1).get()

        if not users_query:
            print(f"User not found: {student_name} ({institution})")
            continue

        user_doc = users_query[0]
        user_ref = user_doc.reference
        user_data = user_doc.to_dict()

        # Find ExamAssignment for this user and procedure
        exam_query = db.collection('ExamAssignment') \
            .where('user', '==', user_ref) \
            .where('procedure_name', '==', proc_name) \
            .limit(1).get()

        if not exam_query:
            print(f"ExamAssignment not found for {student_name} - {proc_name}")
            continue

        exam_doc = exam_query[0]
        exam_ref = exam_doc.reference

        # Prepare update data
        update_data = {
            'marks': marks,
            'institution': institution,
            'procedureName': proc_name,
            'procedure_name': proc_name,
            'skillathon': SKILLATHON_NAME,
            'studentId': user_doc.id,
            'studentName': user_data.get('name', student_name),
            'username': user_data.get('username', user_data.get('emailID', '')),
            'emailID': user_data.get('emailID', ''),
            'gender': user_data.get('gender', user_data.get('learner_gender', 'others')),
            'completed_date': today,
            'status': 'Completed',
        }

        exam_ref.update(update_data)
        print(f"Updated ExamAssignment for {student_name} - {proc_name}")

print("Done.")

