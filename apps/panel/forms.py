from django import forms

class AvatarUpload(forms.Form):
    """Image upload form"""
    avatar = forms.ImageField()

    def clean_avatar(self):
        avatar = self.cleaned_data['avatar']

        try:
            main, sub = avatar.content_type.split('/')
            if not (main == 'image' and sub in ['jpeg', 'pjpeg', 'gif', 'png']):
                raise forms.ValidationError('Image type is not supported')
            if len(avatar) > (300 * 1024):
                raise forms.ValidationError('Avatar file size may not exceed 300k')

        except:
            return None
        return avatar
