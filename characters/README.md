# characters/ folder

Har character ka apna folder, naam cast.json ke "name" ka lowercase:

    characters/shazy/idle.png        <- ZAROORI (pura jism, pairon samet, transparent background behtar)
    characters/shazy/happy.png       <- optional: us emotion ki alag image
    characters/shazy/angry.png       <- optional
    characters/shazy/shocked.png     <- optional
    characters/shazy/idle_talk.png   <- optional: munh khula hua (bolte waqt idle aur idle_talk badalte hain = lip sync)

Emotions jo code samajhta hai: idle, happy, sad, angry, shocked, scared, excited, confused, smug, laugh.
Jo image nahi hogi uski jagah idle.png use hogi (aur code halka tint/hilna-julna khud laga dega).

Image transparent PNG na ho (JPG ya saaf background wali PNG) to code khud background hata leta hai
(sab se bade hisse ko character maan kar). Character sheet se ek pose nikalna ho:

    python tools/cutout.py sheet.jpg characters/ali/idle.png --crop x0,y0,x1,y1

Naya dost: cast.json mein naya entry (name, gender, personality, voice, height_cm) + folder mein image. Bas.
