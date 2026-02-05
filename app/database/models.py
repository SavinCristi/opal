from sqlalchemy import Boolean, Column, Date, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass


#class User(Base):
#    __tablename__ = "user"
#   email: str = Column(String, primary_key=True, index=True)
#   hash_pwd: str = Column(String, nullable=False)
#    name: str = Column(String, nullable=False)

     # One-to-many relationship with Comment
#    designs= relationship('Design', back_populates='user', cascade="all, delete-orphan")

    # One-to-many relationship with Design
#    comments = relationship('Comment', back_populates='user', cascade="all, delete-orphan")

class Design(Base):
    __tablename__ = 'design'
    id: int = Column(Integer, primary_key=True)
    title: str = Column(String, nullable=False)  # Assuming you want a title
    description: str = Column(String)  # Optional description

     # Many-to-one relationship with User
 #   user_email: str = Column(String, ForeignKey('user.email'), nullable=False)
 #   user = relationship('User', back_populates='designs')

    # One-to-many relationship with Comment
    comments = relationship('Comment', back_populates='design', cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = 'comment'
    id: int = Column(Integer, primary_key=True)
    content: str = Column(String, nullable=False)  # Assuming you want to store the content of the comment

   # Many-to-one relationship with Design
    design_id: int = Column(Integer, ForeignKey('design.id'), nullable=False)
    design = relationship('Design', back_populates='comments')
    
    # Many-to-one relationship with User
 #   user_email: str = Column(String, ForeignKey('user.email'), nullable=False)
 #   user = relationship('User', back_populates='comments')

class Organisation(Base):
    __tablename__ = "organisation"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    orgpath = Column(String)
    parent = Column(Integer, ForeignKey("organisation.id"))
    level = Column(String)
    isSSM = Column(Boolean)
    SSM_functions = Column(String)
    approvers = Column(String)
    country = Column(String)

    users = relationship("User", back_populates="organisation", lazy="selectin")


class Institution(Base):
    __tablename__ = "institution"

    id = Column(Integer, primary_key=True, index=True)
    short_name = Column(String)
    long_name = Column(String)
    country = Column(String)
    country_of_residence = Column(String)
    parent = Column(Integer, ForeignKey("institution.id"))
    is_supervised = Column(Boolean)
    is_ = Column(Boolean)
    omi_number = Column(Integer)
    significance = Column(String)

    engagements = relationship("Engagement", back_populates="institution", lazy="selectin")
    

class Engagement(Base):
    __tablename__ = "engagement"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)
    category = Column(String)
    external_reference = Column(String)
    name = Column(String)
    state = Column(String)
    primary_risk_types = Column(String)
    other_risk_types = Column(String)
    purposes = Column(String)
    start_date = Column(Date)
    planned_start_date = Column(Date)
    institution_id = Column(Integer, ForeignKey("institution.id"))
    supervision_type = Column(String)
    significance = Column(String)

    institution = relationship("Institution", back_populates="engagements", lazy="selectin")
    reports = relationship("MissionReport", back_populates="engagement", lazy="selectin")
    users = relationship("UserEngagement", back_populates="engagement", lazy="selectin")
    
class JST(Base):
    __tablename__ = "jst"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)
    category = Column(String)
    external_reference = Column(String)
    name = Column(String)
    
class User(Base):
    __tablename__ = "iam_user"

    name = Column(String, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    orgpath = Column(String)
    isSSM = Column(Boolean)
    SSM_functions = Column(String)
    country = Column(String)
    jobTitle = Column(String)
    level = Column(String)
    organisation_id = Column(Integer, ForeignKey("organisation.id"))
    position = Column(String)
    authority = Column(String)
    team = Column(String)
    org_unit_level_a = Column(String)
    ssmnet_author = Column(Boolean, default=False)

    organisation = relationship("Organisation", back_populates="users", lazy="selectin")
    engagements = relationship("UserEngagement", back_populates="user", lazy="selectin")
    reports_owned = relationship("MissionReport", foreign_keys="[MissionReport.owner_username]", lazy="selectin")
    reports_updated = relationship("MissionReport", foreign_keys="[MissionReport.last_updated_by]", lazy="selectin")

class UserEngagement(Base):
    __tablename__ = "user_engagement"

    id = Column(Integer, primary_key=True)
    user_username = Column(String, ForeignKey("iam_user.name"))
    engagement_id = Column(Integer, ForeignKey("engagement.id"))
    role = Column(String)

    user = relationship("User", back_populates="engagements", lazy="selectin")
    engagement = relationship("Engagement", back_populates="users", lazy="selectin")


class MissionReport(Base):
    __tablename__ = "mission_report"

    id = Column(Integer, primary_key=True)
    engagement_id = Column(Integer, ForeignKey("engagement.id"))
    owner_username = Column(String, ForeignKey("iam_user.name"))
    status = Column(String)
    confidentiality = Column(String)
    last_updated_by = Column(String, ForeignKey("iam_user.name"))

    engagement = relationship("Engagement", back_populates="reports", lazy="selectin")
