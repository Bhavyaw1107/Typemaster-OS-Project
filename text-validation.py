def validate_input(target_text, user_text):
    correct_chars = 0
    errors = 0

    for i, char in enumerate(user_text):
        if i < len(target_text):
            if char == target_text[i]:
                correct_chars += 1
            else:
                errors += 1
        else:
            errors += 1  # Extra characters typed

    return correct_chars, errors


if __name__ == "__main__":
    target = "The quick brown fox"
    user = "The quik brwn fx"
    correct, errors = validate_input(target, user)
    print("Correct:", correct, "Errors:", errors)
