# STT check on demo recordings

Transcribed line by line with Whisper base.en (int8) on CPU on Sat Oct 10, as a stand-in for faster-whisper base.en. Word error rate:

| Call | WER | Words |
|---|---|---|
| normal_bank_fraud_alert | 3.0% | 168 |
| normal_grandson_checkin | 2.0% | 150 |
| scam_bank_code | 1.8% | 163 |
| scam_grandson_bail | 2.6% | 195 |
| scam_irs_warrant | 4.6% | 174 |

All scam keywords (gift cards, Google Play, bail, arrested, police, warrant, Bitcoin, verification code, don't tell, keep this between us, don't hang up) transcribed correctly.

**Gotcha for the rule scorer:** Whisper writes spoken amounts as digits, e.g. 'two thousand dollars' becomes '$2,000'. Match dollar amounts with a regex, not just words.

## normal_bank_fraud_alert
- script: Okay, thank you. I've blocked that charge, and we'll send you a new card in the mail within five to seven days.
  - heard: Okay, thank you. I've blocked that charge and will send you a new card in the mail within 5 to 7 days.
- script: Thanks, Robert. We noticed an unusual charge on your debit card and wanted to check with you. Did you make a purchase at an electronics store in Ohio this morning?
  - heard: Thanks, Robert. We noticed an unusual charge on your debit card and wanted to check with you. Did you make a purchase at an electronic store in Ohio this morning?
- script: Oh good. Do you need anything from me?
  - heard: Oh good, you need anything from me.

## normal_grandson_checkin
- script: Of course you can. The more the merrier. Does he like pumpkin pie?
  - heard: Of course you can be more the merrier, does he like pumpkin pie?
- script: Love you too. Bye Grandma!
  - heard: Love you too, by Grandma.
- script: Ha, perfect. Alright Grandma, I have to run to class. I'll call you on Sunday like always.
  - heard: Ah perfect. Alright grandma, I have to run to class. I'll call you on Sunday like always.

## scam_bank_code
- script: They're trying to wire two thousand dollars overseas. I can freeze your account, but I need to verify that you're the real owner.
  - heard: They're trying to wire $2,000 overseas. I can freeze your account, but I need to verify that you're the real owner.

## scam_grandson_bail
- script: My lawyer says the fastest way is gift cards. Can you go to the store and buy Google Play gift cards? Two thousand dollars.
  - heard: My lawyer says the fastest way is gift cards. Can you go to the store and buy Google Play gift cards? $2,000.
- script: Yeah, I, I have a cold, and I've been crying. Grandma, I'm in really big trouble.
  - heard: Yeah, I have a cold and I've been crying. Grandma, I'm in really big trouble.
- script: Gift cards? For bail? That seems strange.
  - heard: Gift cards for bail that seem strange.

## scam_irs_warrant
- script: Ma'am, our records show you owe four thousand two hundred dollars in back taxes from the last three years.
  - heard: Ma'am, a record show you $04,200 in back taxes from the last three years.
