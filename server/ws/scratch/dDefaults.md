> For the complete documentation index, see [llms.txt](https://docs.maple.finance/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://docs.maple.finance/maple-institutional-for-lenders/defaults-and-impairments.md).

# Defaults and Impairments

### What is a default?

Defaults can be executed by Maple when a borrower has not made a payment (including non-payment or insufficient payment of principal, interest, or late fees as applicable) past the grace period on a loan. A default will:

1. Reduce the pool’s value by the amount of outstanding principal on the loan and any interest accrued.
2. Sell any collateral on the loan and increase the value of the pool to the value of the liquidated collateral.

### What is an Impairment?

The Maple platform gives Maple the ability to impair loans in the event of a potential non-payment or insufficient payment scenario, or in a scenario where a borrower has met another condition of default as articulated in the loan agreement. The impairment is designed to be used in a scenario where the borrower has not yet entered a technical default period, but Maple does not believe that the borrower will be able to repay their loan when it is due. The impairment can be put in place to better distribute potential losses to all current lenders. Impairment prevents a situation where a loan is known to be compromised (by borrower distress or otherwise), and some lenders withdraw their capital prior to the loss, leading to the remaining lenders shouldering more of the burden of the lost capital. This may be done in a situation where Maple believes they will be able to quickly recover a part or all of the loan’s value from the Borrower through collaborative efforts, restructuring, or liquidation collateral. Maple will maintain an active dialog with the Borrower to recover funds through the legal process if necessary.

### How do Impairments affect Deposits and Withdrawals?

When a loan is impaired, its value is temporarily reduced. This allows lenders who want to withdraw to access their capital with a penalty, while not fully defaulting the loan until the grace period has expired. If the Borrower is able to make the payment or repay, it will be changed to unimpaired, and the value of the pool will be restored based on the repayment.

If a lender decides to proceed with withdrawing their funds while the impairment is active, they will have a permanent impairment loss of the difference in value and will be unable to claim any returned capital in the event that there is restitution. Any future recoveries will be pro-rated to those lenders that remained in the pool.

If a new lender decided to deposit into the pool during an impairment, their lending balance will be affected by the impairment. If an impairment is able to be repaid in full, these depositors will be made whole, but will not have any claim to any forfeited recoveries by those who withdrew when the impairment was active.

[Procedure for handling impairments and defaults](https://downloads.eth.maple.finance/docs/Maple_Loan_Default_%26_Impairment_Procedure.pdf)


---

# Agent Instructions
This documentation is published with GitBook. GitBook is the documentation platform designed so that both humans and AI agents can read, navigate, and reason over technical content effectively. Learn more at gitbook.com.

## Querying This Documentation
If you need additional information that is not directly available in this page, you can query the documentation by asking a question.

Perform an HTTP GET request on the following URL with the `ask` and `goal` query parameters:

```
GET https://docs.maple.finance/maple-institutional-for-lenders/defaults-and-impairments.md?ask=<question>&goal=<user_goal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is what the user is ultimately trying to achieve, the reason they need the answer. Sharing it helps GitBook give you a better, more relevant answer. A goal is most helpful when it describes the outcome the user wants rather than restating the question. For example, with `ask=how do I create an API token`, a goal like `automate deployments from our CI pipeline` lets GitBook tailor the answer to that use case.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
