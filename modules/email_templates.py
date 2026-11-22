
def get_email_template(category):

    category = str(category).lower()

    if "hotel" in category:

        return {
            "subject": "Website Development Opportunity for Your Hotel",

            "body": """
Dear {business_name} Team,

I hope you are doing well.

I came across your hotel and wanted to introduce our professional website development services.

A modern website can help your hotel showcase its rooms, facilities, pricing and location while making it easier for guests to enquire about bookings.

Our services include:

• Professional website design
• Mobile-friendly website
• Room and facility showcase
• Contact and enquiry forms
• Google Maps integration

We would appreciate the opportunity to discuss how we can help strengthen your hotel's online presence.

Please let us know if you would be interested in a brief discussion.

Best regards,
Website Development Team
"""
        }

    return {
        "subject": "Website Development Opportunity for Your Restaurant",

        "body": """
Dear {business_name} Team,

I hope you are doing well.

I came across your restaurant and wanted to introduce our professional website development services.

A modern website can help your restaurant showcase its menu, food, location and services while making it easier for customers to discover and contact you.

Our services include:

• Professional website design
• Mobile-friendly website
• Digital menu showcase
• Contact and enquiry forms
• Google Maps integration

We would appreciate the opportunity to discuss how we can help strengthen your restaurant's online presence.

Please let us know if you would be interested in a brief discussion.

Best regards,
Website Development Team
"""
    }
