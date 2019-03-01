from __future__ import absolute_import

import os
import json
import datetime
import openreview
from .. import invitations
from .. import tools

SHORT_BUFFER_MIN = 30
LONG_BUFFER_DAYS = 10

class SubmissionInvitation(openreview.Invitation):

    def __init__(self, conference, start_date, due_date, readers, additional_fields, remove_fields):

        content = invitations.submission.copy()

        if conference.get_subject_areas():
            content['subject_areas'] = {
                'order' : 5,
                'description' : "Select or type subject area",
                'values-dropdown': conference.get_subject_areas(),
                'required': True
            }

        for field in remove_fields:
            del content[field]

        for order, key in enumerate(additional_fields, start=10):
            value = additional_fields[key]
            value['order'] = order
            content[key] = value

        with open(os.path.join(os.path.dirname(__file__), 'templates/submissionProcess.js')) as f:
            file_content = f.read()
            file_content = file_content.replace("var SHORT_PHRASE = '';", "var SHORT_PHRASE = '" + conference.get_short_name() + "';")
            super(SubmissionInvitation, self).__init__(id = conference.get_submission_id(),
                cdate = tools.datetime_millis(start_date),
                duedate = tools.datetime_millis(due_date),
                expdate = tools.datetime_millis(due_date + datetime.timedelta(minutes = SHORT_BUFFER_MIN)),
                readers = ['everyone'],
                writers = [conference.get_id()],
                signatures = [conference.get_id()],
                invitees = ['~'],
                reply = {
                    'forum': None,
                    'replyto': None,
                    'readers': readers,
                    'writers': {
                        'values-copied': [
                            conference.get_id(),
                            '{content.authorids}',
                            '{signatures}'
                        ]
                    },
                    'signatures': {
                        'values-regex': '~.*'
                    },
                    'content': content
                },
                process_string = file_content
            )

class BlindSubmissionsInvitation(openreview.Invitation):

    def __init__(self, conference):
        super(BlindSubmissionsInvitation, self).__init__(id = conference.get_blind_submission_id(),
            readers = ['everyone'],
            writers = [conference.get_id()],
            signatures = [conference.get_id()],
            invitees = ['~'],
            reply = {
                'forum': None,
                'replyto': None,
                'readers': {
                    'values-regex': '.*'
                },
                'writers': {
                    'values': [conference.get_id()]
                },
                'signatures': {
                    'values': [conference.get_id()]
                },
                'content': {
                    'authors': {
                        'values': ['Anonymous']
                    },
                    'authorids': {
                        'values-regex': '.*'
                    }
                }
            }
        )

class SubmissionRevisionInvitation(openreview.Invitation):

    def __init__(self, conference, name, note, start_date, due_date, readers, submission_content, additional_fields, remove_fields):

        content = submission_content.copy()

        for field in remove_fields:
            del content[field]

        for order, key in enumerate(additional_fields, start=10):
            value = additional_fields[key]
            value['order'] = order
            content[key] = value

        with open(os.path.join(os.path.dirname(__file__), 'templates/submissionRevisionProcess.js')) as f:
            file_content = f.read()
            file_content = file_content.replace("var SHORT_PHRASE = '';", "var SHORT_PHRASE = '" + conference.get_short_name() + "';")
            super(SubmissionRevisionInvitation, self).__init__(id = conference.get_id() + '/-/Paper' + str(note.number) + '/' + name,
                cdate = tools.datetime_millis(start_date),
                duedate = tools.datetime_millis(due_date),
                readers = ['everyone'],
                writers = [conference.get_id()],
                signatures = [conference.get_id()],
                invitees = note.content['authorids'] + note.signatures,
                reply = {
                    'forum': note.id,
                    'referent': note.id,
                    'readers': readers,
                    'writers': {
                        'values-copied': [
                            conference.get_id(),
                            '{content.authorids}',
                            '{signatures}'
                        ]
                    },
                    'signatures': {
                        'values-regex': '~.*'
                    },
                    'content': content
                },
                process_string = file_content
            )

class BidInvitation(openreview.Invitation):
    def __init__(self, conference, start_date, due_date, request_count, with_area_chairs):

        readers = [
            conference.get_id(),
            conference.get_program_chairs_id(),
            conference.get_reviewers_id()
        ]

        invitees = [ conference.get_reviewers_id() ]
        if with_area_chairs:
            readers.append(conference.get_area_chairs_id())
            invitees.append(conference.get_area_chairs_id())

        super(BidInvitation, self).__init__(id = conference.get_bid_id(),
            cdate = tools.datetime_millis(start_date),
            duedate = tools.datetime_millis(due_date),
            expdate = tools.datetime_millis(due_date + datetime.timedelta(minutes = SHORT_BUFFER_MIN)),
            readers = readers,
            writers = [conference.get_id()],
            signatures = [conference.get_id()],
            invitees = invitees,
            multiReply = True,
            taskCompletionCount = request_count,
            reply = {
                'forum': None,
                'replyto': None,
                'invitation': conference.get_blind_submission_id(),
                'readers': {
                    'values-copied': [conference.get_id(), '{signatures}']
                },
                'signatures': {
                    'values-regex': '~.*'
                },
                'content': {
                    'tag': {
                        'required': True,
                        'value-radio': [ 'Very High', 'High', 'Neutral', 'Low', 'Very Low']
                    }
                }
            }
        )



class PublicCommentInvitation(openreview.Invitation):

    def __init__(self, conference, name, note, start_date, anonymous = False):

        content = invitations.comment.copy()

        signatures_regex = '~.*'

        if anonymous:
            signatures_regex = '~.*|\\(anonymous\\)'

        with open(os.path.join(os.path.dirname(__file__), 'templates/commentProcess.js')) as f:
            file_content = f.read()
            file_content = file_content.replace("var CONFERENCE_ID = '';", "var CONFERENCE_ID = '" + conference.get_id() + "';")
            file_content = file_content.replace("var SHORT_PHRASE = '';", "var SHORT_PHRASE = '" + conference.get_id() + "';")
            super(PublicCommentInvitation, self).__init__(id = conference.get_id() + '/-/Paper' + str(note.number) + '/' + name,
                cdate = tools.datetime_millis(start_date),
                readers = ['everyone'],
                writers = [conference.get_id()],
                signatures = [conference.get_id()],
                invitees = ['~'],
                noninvitees = [
                    conference.get_authors_id(number = note.number),
                    conference.get_reviewers_id(number = note.number),
                    conference.get_area_chairs_id(number = note.number),
                    conference.get_id() + '/' + "Program_Chairs"
                ],
                reply = {
                    'forum': note.id,
                    'replyto': None,
                    'readers': {
                        "description": "Select all user groups that should be able to read this comment.",
                        "values-dropdown": [
                            "everyone",
                            conference.get_authors_id(number = note.number),
                            conference.get_reviewers_id(number = note.number),
                            conference.get_area_chairs_id(number = note.number),
                            conference.get_id() + '/' + "Program_Chairs"
                        ]
                    },
                    'writers': {
                        'values-copied': [
                            conference.get_id(),
                            '{signatures}'
                        ]
                    },
                    'signatures': {
                        'values-regex': signatures_regex,
                        'description': 'How your identity will be displayed.'
                    },
                    'content': content
                },
                process_string = file_content
            )

class OfficialCommentInvitation(openreview.Invitation):

    def __init__(self, conference, name, note, start_date, anonymous = False):

        content = invitations.comment.copy()

        prefix = conference.get_id() + '/Paper' + str(note.number) + '/'
        signatures_regex = '~.*'

        if anonymous:
            signatures_regex = '{prefix}AnonReviewer[0-9]+|{prefix}{authors_name}|{prefix}Area_Chair[0-9]+|{conference_id}/{program_chairs_name}'.format(prefix=prefix,
            conference_id=conference.id, authors_name = conference.authors_name, program_chairs_name = conference.program_chairs_name)

        with open(os.path.join(os.path.dirname(__file__), 'templates/commentProcess.js')) as f:
            file_content = f.read()

            file_content = file_content.replace("var CONFERENCE_ID = '';", "var CONFERENCE_ID = '" + conference.id + "';")
            file_content = file_content.replace("var SHORT_PHRASE = '';", "var SHORT_PHRASE = '" + conference.short_name + "';")
            file_content = file_content.replace("var AUTHORS_NAME = '';", "var AUTHORS_NAME = '" + conference.authors_name + "';")
            file_content = file_content.replace("var REVIEWERS_NAME = '';", "var REVIEWERS_NAME = '" + conference.reviewers_name + "';")
            file_content = file_content.replace("var AREA_CHAIRS_NAME = '';", "var AREA_CHAIRS_NAME = '" + conference.area_chairs_name + "';")
            file_content = file_content.replace("var PROGRAM_CHAIRS_NAME = '';", "var PROGRAM_CHAIRS_NAME = '" + conference.program_chairs_name + "';")
            super(OfficialCommentInvitation, self).__init__(id = conference.id + '/-/Paper' + str(note.number) + '/' + name,
                cdate = tools.datetime_millis(start_date),
                readers = ['everyone'],
                writers = [conference.id],
                signatures = [conference.id],
                invitees = [
                    conference.get_authors_id(number = note.number),
                    conference.get_reviewers_id(number = note.number),
                    conference.get_area_chairs_id(number = note.number),
                    conference.get_program_chairs_id()
                ],
                reply = {
                    'forum': note.id,
                    'replyto': None,
                    'readers': {
                        "description": "Select all user groups that should be able to read this comment.",
                        "values-dropdown": [
                            conference.get_authors_id(number = note.number),
                            conference.get_reviewers_id(number = note.number),
                            conference.get_area_chairs_id(number = note.number),
                            conference.get_program_chairs_id()
                        ]
                    },
                    'writers': {
                        'values-copied': [
                            conference.id,
                            '{signatures}'
                        ]
                    },
                    'signatures': {
                        'values-regex': signatures_regex,
                        'description': 'How your identity will be displayed.'
                    },
                    'content': content
                },
                process_string = file_content
            )

class ReviewInvitation(openreview.Invitation):

    def __init__(self, conference, name, note, start_date, due_date, public):
        content = invitations.review.copy()

        prefix = conference.get_id() + '/Paper' + str(note.number) + '/'
        readers = ['everyone']

        if not public:
            readers = [
                conference.get_authors_id(number = note.number),
                conference.get_reviewers_id(number = note.number),
                conference.get_area_chairs_id(number = note.number),
                conference.get_program_chairs_id()
            ]

        with open(os.path.join(os.path.dirname(__file__), 'templates/reviewProcess.js')) as f:
            file_content = f.read()

            file_content = file_content.replace("var CONFERENCE_ID = '';", "var CONFERENCE_ID = '" + conference.id + "';")
            file_content = file_content.replace("var SHORT_PHRASE = '';", "var SHORT_PHRASE = '" + conference.short_name + "';")
            file_content = file_content.replace("var AUTHORS_NAME = '';", "var AUTHORS_NAME = '" + conference.authors_name + "';")
            file_content = file_content.replace("var REVIEWERS_NAME = '';", "var REVIEWERS_NAME = '" + conference.reviewers_name + "';")
            file_content = file_content.replace("var AREA_CHAIRS_NAME = '';", "var AREA_CHAIRS_NAME = '" + conference.area_chairs_name + "';")
            file_content = file_content.replace("var PROGRAM_CHAIRS_NAME = '';", "var PROGRAM_CHAIRS_NAME = '" + conference.program_chairs_name + "';")
            super(ReviewInvitation, self).__init__(id = conference.id + '/-/Paper' + str(note.number) + '/' + name,
                cdate = tools.datetime_millis(start_date),
                duedate = tools.datetime_millis(due_date),
                expdate = tools.datetime_millis(due_date + datetime.timedelta(days = LONG_BUFFER_DAYS)),
                readers = ['everyone'],
                writers = [conference.id],
                signatures = [conference.id],
                invitees = [conference.get_reviewers_id(number = note.number)],
                reply = {
                    'forum': note.id,
                    'replyto': note.id,
                    'readers': {
                        "description": "Select all user groups that should be able to read this comment.",
                        "values": readers
                    },
                    'writers': {
                        'values-regex': prefix + 'Anon' + conference.reviewers_name[:-1] + '[0-9]+',
                        'description': 'How your identity will be displayed.'
                    },
                    'signatures': {
                        'values-regex': prefix + 'Anon' + conference.reviewers_name[:-1] + '[0-9]+',
                        'description': 'How your identity will be displayed.'
                    },
                    'content': content
                },
                process_string = file_content
            )

class MetaReviewInvitation(openreview.Invitation):

    def __init__(self, conference, name, note, start_date, due_date, public):
        content = invitations.meta_review.copy()

        readers = ['everyone']

        if not public:
            readers = [
                conference.get_area_chairs_id(note.number),
                conference.get_program_chairs_id()
            ]

        super(MetaReviewInvitation, self).__init__(id = conference.id + '/-/Paper' + str(note.number) + '/' + name,
            cdate = tools.datetime_millis(start_date),
            duedate = tools.datetime_millis(due_date),
            expdate = tools.datetime_millis(due_date + datetime.timedelta(days = LONG_BUFFER_DAYS)),
            readers = ['everyone'],
            writers = [conference.id],
            signatures = [conference.id],
            invitees = [conference.get_area_chairs_id(note.number)],
            reply = {
                'forum': note.id,
                'replyto': note.id,
                'readers': {
                    "description": "Select all user groups that should be able to read this comment.",
                    "values": readers
                },
                'writers': {
                    'values-regex': conference.get_area_chairs_id(note.number)[:-1] + '[0-9]+',
                    'description': 'How your identity will be displayed.'
                },
                'signatures': {
                    'values-regex': conference.get_area_chairs_id(note.number)[:-1] + '[0-9]+',
                    'description': 'How your identity will be displayed.'
                },
                'content': content
            }
        )


class InvitationBuilder(object):

    def __init__(self, client):
        self.client = client

    def __build_options(self, default, options):

        merged_options = {}
        for k in default:
            merged_options[k] = default[k]

        for o in options:
            merged_options[o] = options[o]

        return merged_options

    def set_submission_invitation(self, conference, start_date, due_date, additional_fields, remove_fields):

        readers = {}

        ## TODO: move this to an object
        if conference.double_blind:
            readers = {
                'values-copied': [
                    conference.get_id(),
                    '{content.authorids}',
                    '{signatures}'
                ] + conference.get_original_readers()
            }
        else:
            if conference.submission_public:
                readers = {
                    'values': ['everyone']
                }
            else:
                readers = {
                    'values-copied': [
                        conference.get_id(),
                        '{content.authorids}',
                        '{signatures}'
                    ] + conference.get_submission_readers()
                }

        invitation = SubmissionInvitation(conference = conference,
            start_date = start_date,
            due_date = due_date,
            readers = readers,
            additional_fields = additional_fields,
            remove_fields = remove_fields)

        return self.client.post_invitation(invitation)

    def set_blind_submission_invitation(self, conference):

        invitation = BlindSubmissionsInvitation(conference = conference)

        return  self.client.post_invitation(invitation)

    def set_bid_invitation(self, conference, start_date, due_date, request_count, with_area_chairs):

        invitation = BidInvitation(conference, start_date, due_date, request_count, with_area_chairs)

        return self.client.post_invitation(invitation)

    def set_public_comment_invitation(self, conference, notes, name, start_date, anonymous):

        for note in notes:
            self.client.post_invitation(PublicCommentInvitation(conference, name, note, start_date, anonymous))

    def set_private_comment_invitation(self, conference, notes, name, start_date, anonymous):

        for note in notes:
            self.client.post_invitation(OfficialCommentInvitation(conference, name, note, start_date, anonymous))

    def set_review_invitation(self, conference, notes, name, start_date, due_date, public):

        for note in notes:
            self.client.post_invitation(ReviewInvitation(conference, name, note, start_date, due_date, public))

    def set_meta_review_invitation(self, conference, notes, name, start_date, due_date, public):

        for note in notes:
            self.client.post_invitation(MetaReviewInvitation(conference, name, note, start_date, due_date, public))

    def set_revise_submission_invitation(self, conference, notes, name, start_date, due_date, submission_content, additional_fields, remove_fields):

        readers = {}

        ## TODO: move this to an object
        if conference.double_blind:
            readers = {
                'values-copied': [
                    conference.get_id(),
                    '{content.authorids}',
                    '{signatures}'
                ] + conference.get_original_readers()
            }
        else:
            if conference.submission_public:
                readers = {
                    'values': ['everyone']
                }
            else:
                readers = {
                    'values-copied': [
                        conference.get_id(),
                        '{content.authorids}',
                        '{signatures}'
                    ] + conference.get_submission_readers()
                }

        for note in notes:
            self.client.post_invitation(SubmissionRevisionInvitation(conference, name, note, start_date, due_date, readers, submission_content, additional_fields, remove_fields))

    def set_reviewer_recruiter_invitation(self, conference_id, options = {}):

        default_reply = {
            'forum': None,
            'replyto': None,
            'readers': {
                'values': ['~Super_User1']
            },
            'signatures': {
                'values-regex': '\\(anonymous\\)'
            },
            'writers': {
                'values': []
            },
            'content': invitations.recruitment
        }

        reply = self.__build_options(default_reply, options.get('reply', {}))


        with open(os.path.join(os.path.dirname(__file__), 'templates/recruitReviewersProcess.js')) as f:
            content = f.read()
            content = content.replace("var CONFERENCE_ID = '';", "var CONFERENCE_ID = '" + conference_id + "';")
            content = content.replace("var REVIEWERS_ACCEPTED_ID = '';", "var REVIEWERS_ACCEPTED_ID = '" + options.get('reviewers_accepted_id') + "';")
            content = content.replace("var REVIEWERS_DECLINED_ID = '';", "var REVIEWERS_DECLINED_ID = '" + options.get('reviewers_declined_id') + "';")
            content = content.replace("var HASH_SEED = '';", "var HASH_SEED = '" + options.get('hash_seed') + "';")
            invitation = openreview.Invitation(id = conference_id + '/-/Recruit_' + options.get('reviewers_name', 'Reviewers'),
                duedate = tools.datetime_millis(options.get('due_date', datetime.datetime.now())),
                readers = ['everyone'],
                nonreaders = [],
                invitees = ['everyone'],
                noninvitees = [],
                writers = [conference_id],
                signatures = [conference_id],
                reply = reply,
                process_string = content)

            return self.client.post_invitation(invitation)

    def set_recommendation_invitation(self, conference, start_date, due_date, notes_iterator, assingment_notes_iterator):

        assignment_note_by_forum = {}
        for assignment_note in assingment_notes_iterator:
            assignment_note_by_forum[assignment_note.forum] = assignment_note.content

        # Create super invitation with a webfield
        recommendation_invitation = openreview.Invitation(
            id = conference.get_id() + '/-/Recommendation',
            cdate = tools.datetime_millis(start_date),
            duedate = tools.datetime_millis(due_date),
            readers = [conference.get_program_chairs_id(), conference.get_area_chairs_id()],
            invitees = [],
            writers = [conference.get_id()],
            signatures = [conference.get_id()],
            multiReply = True,
            reply = {
                'invitation': conference.get_blind_submission_id(),
                'readers': {
                    'description': 'The users who will be allowed to read the above content.',
                    'values-copied': [conference.get_id(), '{signatures}']
                },
                'signatures': {
                    'description': 'How your identity will be displayed with the above content.',
                    'values-regex': '~.*'
                },
                'content': {
                    'tag': {
                        'description': 'Recommend a reviewer to review this paper',
                        'order': 1,
                        'required': True,
                        'values-url': '/groups?id=' + conference.get_reviewers_id()
                    }
                }
            }
        )

        recommendation_invitation = self.client.post_invitation(recommendation_invitation)
        # Create subinvitation with different list of reviewers, bid, tpms score.

        for note in notes_iterator:
            reviewers = []
            assignment_note = assignment_note_by_forum.get(note.id)
            if assignment_note:
                for group in assignment_note['assignedGroups']:
                    reviewers.append('{profileId} (A) - Bid: {bid} - Tpms: {tpms}'.format(
                        profileId = group.get('userId'),
                        bid = group.get('scores').get('bid'),
                        tpms = group.get('scores').get('affinity'))
                    )
                for group in assignment_note['alternateGroups']:
                    reviewers.append('{profileId} - Bid: {bid} - Tpms: {tpms}'.format(
                        profileId = group.get('userId'),
                        bid = group.get('scores').get('bid'),
                        tpms = group.get('scores').get('affinity'))
                    )
            else:
                raise openreview.OpenReviewException('Assignment note not found for ' + note.id)
            paper_recommendation_invitation = openreview.Invitation(
                id = conference.get_id() + '/-/Paper{number}/Recommendation'.format(number = note.number),
                super = recommendation_invitation.id,
                invitees = [conference.get_program_chairs_id(), conference.get_id() + '/Paper{number}/Area_Chairs'.format(number = note.number)],
                writers = [conference.get_id()],
                signatures = [conference.get_id()],
                multiReply = True,
                reply = {
                    'forum': note.id,
                    'content': {
                        'tag': {
                            'description': 'Recommend reviewer',
                            'order': 1,
                            'required': True,
                            'values-dropdown': reviewers
                        }
                    }
                }
            )
            paper_recommendation_invitation = self.client.post_invitation(paper_recommendation_invitation)
            print('Posted', paper_recommendation_invitation.id)
