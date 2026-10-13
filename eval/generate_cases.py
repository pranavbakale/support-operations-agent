import json
from pathlib import Path

GROUPS = [
    (
        "refunds-and-charges",
        [
            "Can I get a refund for a purchase from last week?",
            "How long does an approved refund take?",
            "I was charged twice for the same invoice.",
            "There is a card charge I do not recognize.",
            "What is the refund window?",
        ],
    ),
    (
        "password-and-account-access",
        [
            "My password reset link expired.",
            "How long am I locked out after failed login attempts?",
            "Can support set a new password for me?",
            "I cannot sign in to my account.",
            "How long does a reset link work?",
        ],
    ),
    (
        "subscription-changes",
        [
            "When does a plan downgrade take effect?",
            "What happens when I cancel my subscription?",
            "Are upgrades prorated?",
            "I want to change my plan at renewal.",
            "Does cancellation end access immediately?",
        ],
    ),
    (
        "privacy-and-data-requests",
        [
            "How long does a data export take?",
            "I want to delete my account data.",
            "Why are billing records retained?",
            "What verification is needed for deletion?",
            "Can I export the data in my account?",
        ],
    ),
]


def build_cases() -> list[dict]:
    cases = []
    case_number = 1
    accounts = ["acct_1001", "acct_1002", "acct_1003"]
    for expected_slug, prompts in GROUPS:
        for cycle in range(5):
            for prompt in prompts:
                needs_ticket = cycle == 4
                message = (
                    f"{prompt} Please create a ticket for a human agent."
                    if needs_ticket
                    else prompt
                )
                cases.append(
                    {
                        "id": f"case_{case_number:03d}",
                        "account_id": accounts[(case_number - 1) % len(accounts)],
                        "message": message,
                        "expected_citation": expected_slug,
                        "expected_state": "awaiting_approval" if needs_ticket else "answered",
                    }
                )
                case_number += 1
    return cases


def main() -> None:
    destination = Path(__file__).with_name("cases.jsonl")
    destination.write_text(
        "".join(json.dumps(case, separators=(",", ":")) + "\n" for case in build_cases()),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
