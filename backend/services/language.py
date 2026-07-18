from langdetect import detect


def detect_language(text):

    try:

        lang = detect(text)

        if lang == "hi":
            return "hi-IN"

        elif lang == "or":
            return "od-IN"

        else:
            return "en-IN"

    except:

        return "en-IN"