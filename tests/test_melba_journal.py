import openreview
import pytest
import time
import json
import datetime
import random
import os
import re
from selenium.webdriver.common.by import By
from openreview.api import OpenReviewClient
from openreview.api import Note
from openreview.journal import Journal
from openreview.journal import JournalRequest

class TestJournal():


    @pytest.fixture(scope="class")
    def journal(self, openreview_client, helpers):

        eic_client=OpenReviewClient(username='adalca@mit.edu', password=helpers.strong_password)
        eic_client.impersonate('MELBA/Editors_In_Chief')

        requests = openreview_client.get_notes(invitation='openreview.net/Support/-/Journal_Request', content={ 'venue_id': 'MELBA' })

        return JournalRequest.get_journal(eic_client, requests[0].id)      

    def test_setup(self, openreview_client, request_page, selenium, helpers, journal_request):

        ## Support Role
        adrian_client = helpers.create_user('adalca@mit.edu', 'Adrian', 'Dalca')

        ## Editors in Chief
        helpers.create_user('msabuncu@cornell.edu', 'Mert', 'Sabuncu')

        ## Publication Chair
        helpers.create_user('publication@melba.com', 'Publication', 'Chair')


        ## Action Editors
        hoel_client = helpers.create_user('hoel@mail.com', 'Hoel', 'Hervadec')
        aasa_client = helpers.create_user('aasa@mailtwo.com', 'Aasa', 'Feragen')
        xukun_client = helpers.create_user('xukun@mail.com', 'Xukun', 'Liu')
        melisa_client = helpers.create_user('ana@mail.com', 'Ana', 'Martinez')
        celeste_client = helpers.create_user('celesste@mail.com', 'Celeste', 'Martinez')

        ## Reviewers
        david_client=helpers.create_user('rev1@mailone.com', 'MELBARev', 'One')
        javier_client=helpers.create_user('rev2@mailtwo.com', 'MELBARev', 'Two')
        carlos_client=helpers.create_user('rev3@mailthree.com', 'MELBARev', 'Three')
        andrew_client = helpers.create_user('rev4@mailfour.com', 'MELBARev', 'Four')
        hugo_client = helpers.create_user('rev5@mailfive.com', 'MELBARev', 'Five')

        #post journal request form
        request_form = openreview_client.post_note_edit(invitation= 'openreview.net/Support/-/Journal_Request',
            signatures = ['openreview.net/Support'],
            note = Note(
                signatures = ['openreview.net/Support'],
                content = {
                    'official_venue_name': {'value': 'The Journal of Machine Learning for Biomedical Imaging'},
                    'abbreviated_venue_name' : {'value': 'MELBA'},
                    'venue_id': {'value': 'MELBA'},
                    'contact_info': {'value': 'editors@melba-journal.org'},
                    'secret_key': {'value': '1234'},
                    'support_role': {'value': '~Adrian_Dalca1' },
                    'editors': {'value': ['~Mert_Sabuncu1', '~Adrian_Dalca1'] },
                    'website': {'value': 'melba-journal.org' },
                    'settings': {
                        'value': {
                            'submission_public': False,
                            'author_anonymity': True,
                            'assignment_delay': 0,
                            'show_conflict_details': True,
                            'has_publication_chairs': True,
                            'expert_reviewers': False,
                            'submission_additional_fields': {
                                'additional_field': {
                                    'order': 98,
                                    'description': 'this is an additional field',
                                    'value': {
                                        'param': {
                                            'fieldName': 'Enter your comments',
                                            'type': 'string',
                                            'maxLength': 50000,
                                            'markdown': True,
                                            'input': 'textarea'
                                        }
                                    }
                                }                                
                            },
                            'review_additional_fields': {
                                'confidential_comment': {
                                    'order': 98,
                                    'description': 'confidential comment',
                                    'value': {
                                        'param': {
                                            'fieldName': 'confidential comment',
                                            'type': 'string',
                                            'maxLength': 50000,
                                            'markdown': True,
                                            'input': 'textarea'
                                        }
                                    },
                                    'readers': ['MELBA', 'MELBA/Paper${7/content/noteNumber/value}/Action_Editors', '${5/signatures}']
                                }                             
                            }
                        }
                    }
                }
            ))

        helpers.await_queue_edit(openreview_client, request_form['id'])

        request_page(selenium, 'http://localhost:3030/group?id=MELBA', adrian_client.token, wait_for_element='tabs-container')
        tabs = selenium.find_element(By.CLASS_NAME, 'nav-tabs').find_elements(By.TAG_NAME, 'li')
        assert len(tabs) == 4
        assert tabs[0].text == 'Your Consoles'
        assert tabs[1].text == 'Accepted Papers'
        assert tabs[2].text == 'Under Review Submissions'
        assert tabs[3].text == 'All Submissions'

    def test_invite_action_editors(self, journal, openreview_client, request_page, selenium, helpers):

        venue_id = 'MELBA'

        request_notes = openreview_client.get_notes(invitation='openreview.net/Support/-/Journal_Request', content= { 'venue_id': 'MELBA' })
        request_note_id = request_notes[0].id
        journal = JournalRequest.get_journal(openreview_client, request_note_id)
        
        journal.invite_action_editors(message='Test {{fullname}},  {{accept_url}}, {{decline_url}}', subject='[MELBA] Invitation to be an Action Editor', invitees=['new_user@mail.com', 'hoel@mail.com', '~Xukun_Liu1', 'aasa@mailtwo.com', '~Ana_Martinez1'])
        invited_group = openreview_client.get_group(f'{venue_id}/Action_Editors/Invited')
        assert invited_group.members == ['new_user@mail.com', '~Hoel_Hervadec1', '~Xukun_Liu1', '~Aasa_Feragen1', '~Ana_Martinez1']

        messages = openreview_client.get_messages(subject = '[MELBA] Invitation to be an Action Editor')
        assert len(messages) == 5

        for message in messages:
            text = message['content']['text']
            accept_url = re.search('https://.*response=Yes', text).group(0).replace('https://openreview.net', 'http://localhost:3030').replace('&amp;', '&')
            request_page(selenium, accept_url, alert=True)

        helpers.await_queue_edit(openreview_client, invitation = 'MELBA/Action_Editors/-/Recruitment')


        group = openreview_client.get_group(f'{venue_id}/Action_Editors')
        assert len(group.members) == 5
        assert '~Aasa_Feragen1' in group.members

    def test_invite_reviewers(self, journal, openreview_client, request_page, selenium, helpers):

        venue_id = 'MELBA'
        request_notes = openreview_client.get_notes(invitation='openreview.net/Support/-/Journal_Request', content= { 'venue_id': 'MELBA' })
        request_note_id = request_notes[0].id
        journal = JournalRequest.get_journal(openreview_client, request_note_id)

        journal.invite_reviewers(message='Test {{fullname}},  {{accept_url}}, {{decline_url}}', subject='[MELBA] Invitation to be a Reviewer', invitees=['rev1@mailone.com', 'rev4@mailfour.com', 'rev3@mailthree.com', 'rev2@mailtwo.com', 'rev5@mailfive.com'])
        invited_group = openreview_client.get_group(f'{venue_id}/Reviewers/Invited')
        assert invited_group.members == ['~MELBARev_One1', '~MELBARev_Four1', '~MELBARev_Three1', '~MELBARev_Two1', '~MELBARev_Five1']

        messages = openreview_client.get_messages(subject = '[MELBA] Invitation to be a Reviewer')
        assert len(messages) == 5

        for message in messages:
            text = message['content']['text']
            accept_url = re.search('https://.*response=Yes', text).group(0).replace('https://openreview.net', 'http://localhost:3030').replace('&amp;', '&')
            request_page(selenium, accept_url, alert=True)

        helpers.await_queue_edit(openreview_client, invitation = 'MELBA/Reviewers/-/Recruitment')

        group = openreview_client.get_group(f'{venue_id}/Reviewers/Invited')
        assert len(group.members) == 5
        assert '~MELBARev_One1' in group.members

        status = journal.invite_reviewers(message='Test {{fullname}},  {{accept_url}}, {{decline_url}}', subject='[MELBA] Invitation to be a Reviewer', invitees=['rev1@mailone.com'])
        messages = openreview_client.get_messages(to = 'rev1@mailone.com', subject = '[MELBA] Invitation to be a Reviewer')
        assert len(messages) == 1

        assert status.get('already_member')
        assert 'rev1@mailone.com' in status.get('already_member')

    def test_submission(self, journal, openreview_client, test_client, helpers):

        venue_id = journal.venue_id
        test_client = OpenReviewClient(username='test@mail.com', password=helpers.strong_password)

        ## Post the submission 1
        submission_note_1 = test_client.post_note_edit(invitation=f'{venue_id}/-/Submission',
            signatures=['~SomeFirstName_User1'],
            note=Note(
                content={
                    'title': { 'value': 'Paper title' },
                    'abstract': { 'value': 'Paper abstract' },
                    'authors': { 'value': ['Test User', 'Celeste Martinez']},
                    'authorids': { 'value': ['~SomeFirstName_User1', '~Celeste_Martinez1']},
                    'pdf': {'value': '/pdf/' + 'p' * 40 +'.pdf' },
                    'competing_interests': { 'value': 'None beyond the authors normal conflict of interests'},
                    'additional_field': { 'value': 'None beyond the authors normal conflict of interests'},
                    'human_subjects_reporting': { 'value': 'Not applicable'}
                }
            ))

        helpers.await_queue_edit(openreview_client, edit_id=submission_note_1['id'])
        note_id_1 = submission_note_1['note']['id']

        Journal.update_affinity_scores(openreview.api.OpenReviewClient(username='openreview.net', password=helpers.strong_password), support_group_id='openreview.net/Support')

        openreview_client.get_invitation('MELBA/Paper1/Action_Editors/-/Recommendation')        

        messages = openreview_client.get_messages(to = 'test@mail.com', subject = '[MELBA] Suggest candidate Action Editor for your new MELBA submission')
        assert len(messages) == 1
        assert messages[0]['content']['text'] == '''Hi SomeFirstName User,

Thank you for submitting your work titled "Paper title" to MELBA.

Before the review process starts, you need to submit three or more recommendations for an Action Editor that you believe has the expertise to oversee the evaluation of your work.

To do so, please follow this link: https://openreview.net/invitation?id=MELBA/Paper1/Action_Editors/-/Recommendation or check your tasks in the Author Console: https://openreview.net/group?id=MELBA/Authors

For more details and guidelines on the MELBA review process, visit melba-journal.org.

The MELBA Editors-in-Chief


Please note that responding to this email will direct your reply to editors@melba-journal.org.
'''

    def test_ae_assignment(self, journal, openreview_client, test_client, helpers):

        venue_id = journal.venue_id
        
        aasa_client = OpenReviewClient(username='aasa@mailtwo.com', password=helpers.strong_password)
        eic_client = OpenReviewClient(username='adalca@mit.edu', password=helpers.strong_password)
        test_client = OpenReviewClient(username='test@mail.com', password=helpers.strong_password)
        
        note = openreview_client.get_notes(invitation='MELBA/-/Submission')[0]
        note_id_1 = note.id
        #journal.invitation_builder.expire_paper_invitations(note)

        journal.setup_ae_assignment(note)

        conflicts = openreview_client.get_edges(invitation='MELBA/Action_Editors/-/Conflict', head=note_id_1)
        assert conflicts
        assert conflicts[0].label == 'mail.com'

        # Assign Action Editor
        editor_in_chief_group_id = 'MELBA/Editors_In_Chief'
        paper_assignment_edge = eic_client.post_edge(openreview.Edge(invitation='MELBA/Action_Editors/-/Assignment',
            readers=[venue_id, editor_in_chief_group_id, '~Aasa_Feragen1'],
            writers=[venue_id, editor_in_chief_group_id],
            signatures=[editor_in_chief_group_id],
            head=note_id_1,
            tail='~Aasa_Feragen1',
            weight=1
        ))

        helpers.await_queue_edit(openreview_client, edit_id=paper_assignment_edge.id)

        aasa_paper1_anon_groups = aasa_client.get_groups(prefix=f'MELBA/Paper1/Action_Editor_.*', signatory='~Aasa_Feragen1')
        assert len(aasa_paper1_anon_groups) == 1
        aasa_paper1_anon_group = aasa_paper1_anon_groups[0]         

        ## Accept the submission 1
        under_review_note = aasa_client.post_note_edit(invitation= 'MELBA/Paper1/-/Review_Approval',
                                    signatures=[aasa_paper1_anon_group.id],
                                    note=Note(content={
                                        'under_review': { 'value': 'Appropriate for Review' }
                                    }))

        helpers.await_queue_edit(openreview_client, edit_id=under_review_note['id'])

        note = aasa_client.get_note(note_id_1)
        assert note
        assert note.invitations == ['MELBA/-/Submission', 'MELBA/-/Edit', 'MELBA/-/Under_Review']

        edits = openreview_client.get_note_edits(note.id, invitation='MELBA/-/Under_Review')
        helpers.await_queue_edit(openreview_client, edit_id=edits[0].id)        

        assert aasa_client.get_invitation('MELBA/Paper1/Reviewers/-/Assignment')

        # Assign reviewer 1
        paper_assignment_edge = aasa_client.post_edge(openreview.Edge(invitation='MELBA/Reviewers/-/Assignment',
            readers=[venue_id, f"{venue_id}/Paper1/Action_Editors", '~MELBARev_One1'],
            nonreaders=[f"{venue_id}/Paper1/Authors"],
            writers=[venue_id, f"{venue_id}/Paper1/Action_Editors"],
            signatures=[aasa_paper1_anon_group.id],
            head=note_id_1,
            tail='~MELBARev_One1',
            weight=1
        ))
        
        # Assign reviewer 2
        paper_assignment_edge = aasa_client.post_edge(openreview.Edge(invitation='MELBA/Reviewers/-/Assignment',
            readers=[venue_id, f"{venue_id}/Paper1/Action_Editors", '~MELBARev_Two1'],
            nonreaders=[f"{venue_id}/Paper1/Authors"],
            writers=[venue_id, f"{venue_id}/Paper1/Action_Editors"],
            signatures=[aasa_paper1_anon_group.id],
            head=note_id_1,
            tail='~MELBARev_Two1',
            weight=1
        ))

        # Assign reviewer 3
        paper_assignment_edge = aasa_client.post_edge(openreview.Edge(invitation='MELBA/Reviewers/-/Assignment',
            readers=[venue_id, f"{venue_id}/Paper1/Action_Editors", '~MELBARev_Three1'],
            nonreaders=[f"{venue_id}/Paper1/Authors"],
            writers=[venue_id, f"{venue_id}/Paper1/Action_Editors"],
            signatures=[aasa_paper1_anon_group.id],
            head=note_id_1,
            tail='~MELBARev_Three1',
            weight=1
        ))

        ## Post a review edit
        reviewer_one_client = OpenReviewClient(username='rev1@mailone.com', password=helpers.strong_password)
        reviewer_one_anon_groups=reviewer_one_client.get_groups(prefix=f'{venue_id}/Paper1/Reviewer_.*', signatory='~MELBARev_One1')

        edges = reviewer_one_client.get_grouped_edges(invitation=f'{venue_id}/Reviewers/-/Pending_Reviews', groupby='weight')
        assert len(edges) == 1
        assert edges[0]['values'][0]['weight'] == 1
        
        review_note = reviewer_one_client.post_note_edit(invitation=f'{venue_id}/Paper1/-/Review',
            signatures=[reviewer_one_anon_groups[0].id],
            note=Note(
                content={
                    'summary_of_contributions': { 'value': 'summary_of_contributions' },
                    'strengths_and_weaknesses': { 'value': 'strengths_and_weaknesses' },
                    'requested_changes': { 'value': 'requested_changes' },
                    'broader_impact_concerns': { 'value': 'broader_impact_concerns' },
                    'claims_and_evidence': { 'value': 'Yes' },
                    'audience': { 'value': 'Yes' },
                    'confidential_comment': { 'value': 'confidential_comment' }
                }
            )
        )

        helpers.await_queue_edit(openreview_client, edit_id=review_note['id'], process_index=0)
        helpers.await_queue_edit(openreview_client, edit_id=review_note['id'], process_index=1)

        edges = reviewer_one_client.get_grouped_edges(invitation=f'{venue_id}/Reviewers/-/Pending_Reviews', groupby='weight')
        assert len(edges) == 1
        assert edges[0]['values'][0]['weight'] == 0

        logs = openreview_client.get_process_logs(invitation=f'{venue_id}/Paper1/-/Review', status='ok')
        assert logs and len(logs) == 2

        reviewer_two_client = OpenReviewClient(username='rev2@mailtwo.com', password=helpers.strong_password)
        reviewer_two_anon_groups=reviewer_two_client.get_groups(prefix=f'{venue_id}/Paper1/Reviewer_.*', signatory='~MELBARev_Two1')
    
        review_note = reviewer_two_client.post_note_edit(invitation=f'{venue_id}/Paper1/-/Review',
            signatures=[reviewer_two_anon_groups[0].id],
            note=Note(
                content={
                    'summary_of_contributions': { 'value': 'summary_of_contributions' },
                    'strengths_and_weaknesses': { 'value': 'strengths_and_weaknesses' },
                    'requested_changes': { 'value': 'requested_changes' },
                    'broader_impact_concerns': { 'value': 'broader_impact_concerns' },
                    'claims_and_evidence': { 'value': 'Yes' },
                    'audience': { 'value': 'Yes' },
                    'confidential_comment': { 'value': 'confidential_comment' }
                }
            )
        )

        helpers.await_queue_edit(openreview_client, edit_id=review_note['id'], process_index=0)
        helpers.await_queue_edit(openreview_client, edit_id=review_note['id'], process_index=1)

        reviewer_three_client = OpenReviewClient(username='rev3@mailthree.com', password=helpers.strong_password)
        reviewer_three_anon_groups=reviewer_two_client.get_groups(prefix=f'{venue_id}/Paper1/Reviewer_.*', signatory='~MELBARev_Three1')

        review_note = reviewer_three_client.post_note_edit(invitation=f'{venue_id}/Paper1/-/Review',
            signatures=[reviewer_three_anon_groups[0].id],
            note=Note(
                content={
                    'summary_of_contributions': { 'value': 'summary_of_contributions' },
                    'strengths_and_weaknesses': { 'value': 'strengths_and_weaknesses' },
                    'requested_changes': { 'value': 'requested_changes' },
                    'broader_impact_concerns': { 'value': 'broader_impact_concerns' },
                    'claims_and_evidence': { 'value': 'Yes' },
                    'audience': { 'value': 'Yes' },
                    'confidential_comment': { 'value': 'confidential_comment' }
                }
            )
        )

        helpers.await_queue_edit(openreview_client, edit_id=review_note['id'], process_index=0)
        helpers.await_queue_edit(openreview_client, edit_id=review_note['id'], process_index=1)

        reviews=openreview_client.get_notes(forum=note_id_1, invitation=f'{venue_id}/Paper1/-/Review', sort='number:desc')
        assert len(reviews) == 3
        assert reviews[0].readers == [f"{venue_id}/Editors_In_Chief", f"{venue_id}/Action_Editors", f"{venue_id}/Paper1/Reviewers", f"{venue_id}/Paper1/Authors"]
        assert reviews[1].readers == [f"{venue_id}/Editors_In_Chief", f"{venue_id}/Action_Editors", f"{venue_id}/Paper1/Reviewers", f"{venue_id}/Paper1/Authors"]
        assert reviews[2].readers == [f"{venue_id}/Editors_In_Chief", f"{venue_id}/Action_Editors", f"{venue_id}/Paper1/Reviewers", f"{venue_id}/Paper1/Authors"]

        invitation = eic_client.get_invitation(f'{venue_id}/Paper1/-/Official_Recommendation')
        assert invitation.cdate > openreview.tools.datetime_millis(datetime.datetime.now())

        eic_client.post_invitation_edit(
            invitations='MELBA/-/Edit',
            readers=[venue_id],
            writers=[venue_id],
            signatures=[venue_id],
            invitation=openreview.api.Invitation(id=f'{venue_id}/Paper1/-/Official_Recommendation',
                cdate=openreview.tools.datetime_millis(datetime.datetime.now()) + 1000,
                signatures=['MELBA/Editors_In_Chief']
            )
        )

        time.sleep(5) ## wait until the process function runs

        ## Post a review recommendation
        official_recommendation_note = reviewer_one_client.post_note_edit(invitation=f'{venue_id}/Paper1/-/Official_Recommendation',
            signatures=[reviewer_one_anon_groups[0].id],
            note=Note(
                content={
                    'decision_recommendation': { 'value': 'Accept' },
                    'claims_and_evidence': { 'value': 'Yes' },
                    'audience': { 'value': 'Yes' }                  
                }
            )
        )

        helpers.await_queue_edit(openreview_client, edit_id=official_recommendation_note['id'])

        official_recommendation_note = reviewer_two_client.post_note_edit(invitation=f'{venue_id}/Paper1/-/Official_Recommendation',
            signatures=[reviewer_two_anon_groups[0].id],
            note=Note(
                content={
                    'decision_recommendation': { 'value': 'Accept' },
                    'claims_and_evidence': { 'value': 'Yes' },
                    'audience': { 'value': 'Yes' }                  
                }
            )
        )

        helpers.await_queue_edit(openreview_client, edit_id=official_recommendation_note['id']) 

        official_recommendation_note = reviewer_three_client.post_note_edit(invitation=f'{venue_id}/Paper1/-/Official_Recommendation',
            signatures=[reviewer_three_anon_groups[0].id],
            note=Note(
                content={
                    'decision_recommendation': { 'value': 'Accept' },
                    'claims_and_evidence': { 'value': 'Yes' },
                    'audience': { 'value': 'Yes' }                  
                }
            )
        )

        helpers.await_queue_edit(openreview_client, edit_id=official_recommendation_note['id'])

        reviews=openreview_client.get_notes(forum=note_id_1, invitation=f'{venue_id}/Paper1/-/Review', sort= 'number:asc')
        
        for review in reviews:
            signature=review.signatures[0]
            rating_note=aasa_client.post_note_edit(invitation=f'{signature}/-/Rating',
                signatures=[aasa_paper1_anon_group.id],
                note=Note(
                    content={
                        'rating': { 'value': 'Exceeds expectations' }
                    }
                )
            )
            helpers.await_queue_edit(openreview_client, edit_id=rating_note['id'])
            process_logs = openreview_client.get_process_logs(id = rating_note['id'])
            assert len(process_logs) == 1
            assert process_logs[0]['status'] == 'ok'

        decision_note = aasa_client.post_note_edit(invitation=f'{venue_id}/Paper1/-/Decision',
            signatures=[aasa_paper1_anon_group.id],
            note=Note(
                content={
                    'claims_and_evidence': { 'value': 'Accept as is' },
                    'audience': { 'value': 'Accept as is' },
                    'recommendation': { 'value': 'Accept as is' },
                    'comment': { 'value': 'This is a nice paper!' }
                }
            )
        )

        helpers.await_queue_edit(openreview_client, edit_id=decision_note['id'])

        decision_note = aasa_client.get_note(decision_note['note']['id'])
        assert decision_note.readers == [f"{venue_id}/Editors_In_Chief", f"{venue_id}/Paper1/Action_Editors"]

        ## EIC approves the decision
        approval_note = eic_client.post_note_edit(invitation='MELBA/Paper1/-/Decision_Approval',
                            signatures=['MELBA/Editors_In_Chief'],
                            note=Note(
                                content= {
                                    'approval': { 'value': 'I approve the AE\'s decision.' },
                                    'comment_to_the_AE': { 'value': 'I agree with the AE' }
                                }
                            ))

        helpers.await_queue_edit(openreview_client, edit_id=approval_note['id'])

        decision_note = eic_client.get_note(decision_note.id)
        assert decision_note.readers == [f"{venue_id}/Editors_In_Chief", f"{venue_id}/Action_Editors", f"{venue_id}/Paper1/Reviewers", f"{venue_id}/Paper1/Authors"]
        assert decision_note.nonreaders == []

        ## post a revision
        revision_note = test_client.post_note_edit(invitation=f'{venue_id}/Paper1/-/Camera_Ready_Revision',
            signatures=[f"{venue_id}/Paper1/Authors"],
            note=Note(
                content={
                    'title': { 'value': 'Paper title VERSION 2' },
                    'authors': { 'value': ['Test User', 'Celeste Martinez']},
                    'authorids': { 'value': ['~SomeFirstName_User1', '~Celeste_Martinez1']},
                    'abstract': { 'value': 'Paper abstract' },
                    'pdf': {'value': '/pdf/' + 'p' * 40 +'.pdf' },
                    'supplementary_material': { 'value': '/attachment/' + 's' * 40 +'.zip'},
                    'competing_interests': { 'value': 'None beyond the authors normal conflict of interests'},
                    'human_subjects_reporting': { 'value': 'Not applicable'},
                    'video': { 'value': 'https://youtube.com/dfenxkw'},
                    'additional_field': { 'value': 'None beyond the authors normal conflict of interests'}   
                }
            )
        )

        helpers.await_queue_edit(openreview_client, edit_id=revision_note['id'])

        ## AE verifies the camera ready revision
        openreview_client.add_members_to_group('MELBA/Publication_Chairs', 'publication@melba.com')
        publication_chair_client = OpenReviewClient(username='publication@melba.com', password=helpers.strong_password)
        submission_note = publication_chair_client.get_note(note_id_1)
        verification_note = publication_chair_client.post_note_edit(invitation='MELBA/Paper1/-/Camera_Ready_Verification',
                            signatures=[f"{venue_id}/Publication_Chairs"],
                            note=Note(
                                signatures=[f"{venue_id}/Publication_Chairs"],
                                content= {
                                    'verification': { 'value': 'I confirm that camera ready manuscript complies with the MELBA stylefile and, if appropriate, includes the minor revisions that were requested.' }
                                 }
                            ))

        journal.invitation_builder.expire_paper_invitations(note)
        journal.invitation_builder.expire_reviewer_responsibility_invitations()
        journal.invitation_builder.expire_assignment_availability_invitations()                