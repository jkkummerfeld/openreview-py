def process(client, invitation):

    domain = client.get_group(invitation.domain)
    venue_id = domain.id
    submission_venue_id = domain.content['submission_venue_id']['value']
    rejected_venue_id = domain.content['rejected_venue_id']['value']
    meta_invitation_id = domain.content['meta_invitation_id']['value']
    submission_name = domain.content['submission_name']['value']
    decision_name = domain.content.get('decision_name', {}).get('value', 'Decision')
    decision_field_name = domain.content.get('decision_field_name', {}).get('value', 'decision')
    accept_options = domain.content.get('accept_decision_options', {}).get('value')
    review_name = domain.content.get('review_name', {}).get('value')
    meta_review_name = domain.content.get('meta_review_name', {}).get('value')
    rebuttal_name = domain.content.get('rebuttal_name', {}).get('value')
    ethics_chairs_id = domain.content.get('ethics_chairs_id', {}).get('value')
    ethics_reviewers_name = domain.content.get('ethics_reviewers_name', {}).get('value')
    release_to_ethics_chairs = domain.get_content_value('release_submissions_to_ethics_chairs')

    now = openreview.tools.datetime_millis(datetime.datetime.now())
    cdate = invitation.edit['invitation']['cdate'] if 'cdate' in invitation.edit['invitation'] else invitation.cdate

    if cdate > now and not client.get_invitations(invitation=invitation.id, limit=1):
        ## invitation is in the future, do not process
        print('invitation is not yet active and no child invitations created', cdate)
        return

    def delete_invitation(child_invitation, ddate):
        client.post_invitation_edit(
            invitations=meta_invitation_id,
            readers=[venue_id],
            writers=[venue_id],
            signatures=[venue_id],
            invitation=openreview.api.Invitation(
                id=child_invitation.id,
                ddate=ddate
            )
        )
    
    def get_children_notes():
        source = openreview.tools.get_invitation_source(invitation, domain)

        ## TODO: use tools.should_match_invitation_source when "all_submissions" is removed
        def filter_by_source(source):

            venueids = source.get('venueid', [submission_venue_id]) ## we should always have a venueid
            source_submissions = client.get_all_notes(content={ 'venueid': ','.join([venueids] if isinstance(venueids, str) else venueids) }, sort='number:asc', details='replies')

            ## Keep backward compatibility with 'all_submissions' before and after running the post_decision_stage
            if not source_submissions:
                source_submissions = client.get_all_notes(content={ 'venueid': ','.join([venue_id, rejected_venue_id]) }, sort='number:asc', details='replies')
            
            if 'with_decision_accept' in source:
                source_submissions = [s for s in source_submissions 
                                      if len([r for r in s.details['replies'] 
                                        if f'{venue_id}/{submission_name}{s.number}/-/{decision_name}' in r['invitations'] 
                                        and openreview.tools.is_accept_decision(r['content'][decision_field_name]['value'], accept_options) == source.get('with_decision_accept')]) > 0]

            if 'readers' in source:
                source_submissions = [s for s in source_submissions if set(source['readers']).issubset(set(s.readers))]

            if 'content' in source:
                for key, value in source.get('content', {}).items():
                    source_submissions = [s for s in source_submissions if value == s.content.get(key, {}).get('value')]

            if 'reply_to' in source:
                source_submissions = [(openreview.api.Note.from_json(reply), s) for s in source_submissions for reply in s.details['replies'] if reply['invitations'][0].endswith(f'/-/{source.get("reply_to")}')]
            else:
                source_submissions = [(note, note) for note in source_submissions]

            return source_submissions

        return filter_by_source(source)
    
    def update_note_readers(submission, paper_invitation):
        ## Update readers of current notes
        notes = client.get_notes(invitation=paper_invitation.id)
        invitation_readers = paper_invitation.edit['note'].get('readers', [])

        ## if invitation has param in readers, we ignore the update
        if 'param' in invitation_readers:
            return

        ## if the invitation indicates readers is everyone but the submission is not, we ignore the update
        if 'everyone' in invitation_readers and 'everyone' not in submission.readers:
            return

        def updated_content_readers(note, paper_inv):
            updated_content = {}
            if 'content' not in paper_inv.edit['note']:
                return updated_content
            invitation_content = paper_inv.edit['note']['content']
            for key in invitation_content.keys():
                content_readers = invitation_content[key].get('readers', [])
                final_content_readers = list(dict.fromkeys([note.signatures[0] if 'signatures' in r else r for r in content_readers]))
                if note.content.get(key, {}).get('readers', []) != final_content_readers:
                    updated_content[key] = {
                        'readers': final_content_readers if final_content_readers else { 'delete': True }
                    }
            return updated_content

        for note in notes:
            final_invitation_readers = list(dict.fromkeys([note.signatures[0] if 'signatures' in r else r for r in invitation_readers]))
            edit_readers = list(dict.fromkeys([note.signatures[0] if 'signatures' in r else r for r in paper_invitation.edit.get('readers',[])]))
            if len(edit_readers) == 1 and '{2/note/readers}' in edit_readers[0]:
                edit_readers = final_invitation_readers
            updated_content = updated_content_readers(note, paper_invitation)
            updated_note = openreview.api.Note(
                id = note.id
            )
            final_invitation_writers = list(dict.fromkeys([note.signatures[0] if 'signatures' in r else r for r in paper_invitation.edit['note'].get('writers', [])]))
            
            if final_invitation_readers and note.readers != final_invitation_readers:
                updated_note.readers = final_invitation_readers
                updated_note.nonreaders = paper_invitation.edit['note'].get('nonreaders')
            if final_invitation_writers and note.writers != final_invitation_writers:
                updated_note.writers = final_invitation_writers
            if updated_content:
                updated_note.content = updated_content
            if updated_note.content or updated_note.readers or updated_note.writers:
                client.post_note_edit(
                    invitation = meta_invitation_id,
                    readers = edit_readers,
                    nonreaders = paper_invitation.edit['note'].get('nonreaders'),
                    writers = [venue_id],
                    signatures = [venue_id],
                    note = updated_note
                )

    def post_invitation(note):

        note, forumNote = note

        def find_note_from_details(note_id):
            if note_id == forumNote.id:
                return forumNote            
            for reply in forumNote.details['replies']:
                if reply['id'] == note_id:
                    return openreview.api.Note.from_json(reply)
            return None
        
        content = {
            'noteId': { 'value': forumNote.id },
            'noteNumber': { 'value': forumNote.number }
        }

        if 'replyto' in invitation.edit['content']:
            content['replyto'] = { 'value': note.id }

        if 'replytoSignatures' in invitation.edit['content']:
            content['replytoSignatures'] = { 'value': note.signatures[0] }

        if 'replyNumber' in invitation.edit['content']:
            content['replyNumber'] = { 'value': note.number }

        if 'invitationPrefix' in invitation.edit['content']:
            content['invitationPrefix'] = { 'value': note.invitations[0].replace('/-/', '/') + str(note.number) }

        if 'replytoReplytoSignatures' in invitation.edit['content']:
            replyto_note = find_note_from_details(note.replyto)
            if replyto_note:
                content['replytoReplytoSignatures'] = { 'value': replyto_note.signatures[0] }             

        if 'noteReaders' in invitation.edit['content']:
            paper_readers = invitation.content.get('review_readers',{}).get('value') or invitation.content.get('comment_readers',{}).get('value')
            final_readers = []
            final_readers.extend(paper_readers)
            final_readers = [reader.replace('{number}', str(note.number)) for reader in final_readers]
            if '{signatures}' in final_readers:
                final_readers.remove('{signatures}')
            if note.content.get('flagged_for_ethics_review', {}).get('value', False):
                if 'everyone' not in final_readers or invitation.content.get('reader_selection',{}).get('value'):
                    final_readers.append(f'{venue_id}/{submission_name}{note.number}/{ethics_reviewers_name}')
                    if release_to_ethics_chairs:
                        final_readers.append(ethics_chairs_id)
            content['noteReaders'] = { 'value': final_readers }

        paper_invitation_edit = client.post_invitation_edit(invitations=invitation.id,
            readers=[venue_id],
            writers=[venue_id],
            signatures=[venue_id],
            content=content,
            invitation=openreview.api.Invitation()
        )
        paper_invitation = client.get_invitation(paper_invitation_edit['invitation']['id'])
        if paper_invitation.edit and paper_invitation.edit.get('note'):
            update_note_readers(note, paper_invitation)

        return paper_invitation

    notes = get_children_notes()

    current_child_invitations = client.get_all_invitations(invitation=invitation.id)

    print(f'create or update {len(notes)} child invitations')
    posted_invitations = openreview.tools.concurrent_requests(post_invitation, notes, desc=f'edit_invitation_process')
    posted_invitations_by_id = { i.id: i for i in posted_invitations}

    for current_invitation in current_child_invitations:
        if current_invitation.id not in posted_invitations_by_id:
            delete_invitation(current_invitation, now)